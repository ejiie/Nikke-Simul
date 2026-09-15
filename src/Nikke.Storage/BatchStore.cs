using Microsoft.Data.Sqlite;
using Nikke.Contracts;

namespace Nikke.Storage;

public record StoredExperiment(BatchStatus Status, string Prepared, ExperimentRequest Request);
public record RunWrite(int Index, int Attempt, RunSummary? Summary, string? ErrorCode);

// Separate compute database. The API's existing single-instance lock owns its lifetime.
public sealed class BatchStore
{
    private readonly string connectionString;
    private readonly object gate = new();
    public BatchStore(string computeRoot)
    {
        Directory.CreateDirectory(computeRoot);
        connectionString=new SqliteConnectionStringBuilder {DataSource=Path.Combine(computeRoot,"batches.db"),Pooling=false}.ToString();
        using var db=Open();
        Execute(db,"PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY, state TEXT NOT NULL, attempt INTEGER NOT NULL, input TEXT NOT NULL, prepared TEXT NOT NULL, request TEXT NOT NULL, selection TEXT NOT NULL, error TEXT); CREATE TABLE IF NOT EXISTS batch_runs(batch TEXT NOT NULL, idx INTEGER NOT NULL, attempt INTEGER NOT NULL, payload TEXT, error TEXT, PRIMARY KEY(batch,idx));");
        Execute(db,"UPDATE experiments SET state='cancelled',error='process_interrupted' WHERE state IN ('queued','running','cancelling')");
    }
    private SqliteConnection Open() {var db=new SqliteConnection(connectionString);db.Open();return db;}
    private static SqliteCommand Command(SqliteConnection db,string sql,params (string,object?)[] args)
    {var c=db.CreateCommand();c.CommandText=sql;foreach(var (key,value) in args)c.Parameters.AddWithValue(key,value??DBNull.Value);return c;}
    private static void Execute(SqliteConnection db,string sql,params (string,object?)[] args)
    {using var c=Command(db,sql,args);c.ExecuteNonQuery();}
    public BatchStatus Create(IPreparedExperiment prepared, ExperimentRequest request, ExecutionSelection selection)
    {
        var id=Guid.NewGuid().ToString("N");
        lock(gate) {using var db=Open();Execute(db,"INSERT INTO experiments VALUES($id,'queued',1,$input,$prepared,$request,$selection,NULL)",
            ("$id",id),("$input",Wire.Serialize(prepared.Input)),("$prepared",prepared.PersistedInput),("$request",Wire.Serialize(request)),("$selection",Wire.Serialize(selection)));}
        return Read(id).Status;
    }
    public StoredExperiment Read(string id)
    {
        lock(gate) {using var db=Open();using var c=Command(db,"SELECT state,attempt,input,prepared,request,selection,error,(SELECT COUNT(*) FROM batch_runs WHERE batch=$id AND payload IS NOT NULL),(SELECT COUNT(*) FROM batch_runs WHERE batch=$id AND payload IS NULL) FROM experiments WHERE id=$id",("$id",id));
            using var r=c.ExecuteReader();if(!r.Read())throw new KeyNotFoundException();
            var request=Wire.Read<ExperimentRequest>(r.GetString(4));int valid=r.GetInt32(7),failed=r.GetInt32(8);string state=r.GetString(0);
            var status=new BatchStatus(id,state,r.GetInt32(1),request.Runs,valid,failed,state=="cancelled"?request.Runs-valid-failed:0,
                valid<request.Runs,Wire.Read<ExperimentInput>(r.GetString(2)),Wire.Read<ExecutionSelection>(r.GetString(5)),r.IsDBNull(6)?null:r.GetString(6));
            return new(status,r.GetString(3),request); }
    }
    public void Running(string id,int attempt,ExecutionSelection selection)
    {lock(gate){using var db=Open();Execute(db,"UPDATE experiments SET state='running',selection=$selection WHERE id=$id AND attempt=$attempt AND state='queued'",("$id",id),("$attempt",attempt),("$selection",Wire.Serialize(selection)));}}
    public void Cancel(string id)
    {lock(gate){using var db=Open();Execute(db,"UPDATE experiments SET state='cancelling' WHERE id=$id AND state IN ('queued','running')",("$id",id));}}
    public BatchStatus Resume(string id)
    {
        lock(gate){var current=Read(id).Status;if(current.State is not ("cancelled" or "failed"))throw new InvalidOperationException("batch_not_resumable");
            using var db=Open();using var tx=db.BeginTransaction();
            Execute(db,"DELETE FROM batch_runs WHERE batch=$id AND payload IS NULL",("$id",id));
            Execute(db,"UPDATE experiments SET state='queued',attempt=attempt+1,error=NULL WHERE id=$id",("$id",id));tx.Commit();return Read(id).Status;}
    }
    public HashSet<int> ValidIndices(string id)
    {lock(gate){using var db=Open();using var c=Command(db,"SELECT idx FROM batch_runs WHERE batch=$id AND payload IS NOT NULL",("$id",id));using var r=c.ExecuteReader();var result=new HashSet<int>();while(r.Read())result.Add(r.GetInt32(0));return result;}}
    public void Write(string id,int attempt,IReadOnlyList<RunWrite> rows)
    {
        lock(gate){var batch=Read(id).Status;if(batch.Attempt!=attempt || batch.State!="running")return;
            using var db=Open();using var tx=db.BeginTransaction();
            foreach(var row in rows)
            {
                if(row.Attempt!=attempt || row.Index<0 || row.Index>=batch.Requested)throw new ArgumentException("invalid_run_identity");
                if(row.Summary is {} run && (run.ExperimentId!=id || run.Attempt!=attempt || run.Index!=row.Index || run.RunId!=$"{id}:{row.Index}"
                    || run.InputFingerprint!=batch.Input.Fingerprint || run.Backend!=batch.Execution.Backend || run.Phase!=batch.Input.Phase
                    || !double.IsFinite(run.TeamDamage) || run.TeamDamage<0 || run.Members.Count!=5
                    || !double.IsFinite(run.ElapsedMilliseconds) || run.ElapsedMilliseconds<0 || run.FullBursts<0
                    || !run.Members.Select(m=>m.CharacterId).SequenceEqual(batch.Input.CharacterIds)
                    || run.Members.Any(m=>!double.IsFinite(m.Damage)||m.Damage<0 || m.Shots<0 || m.Hits<0 || m.CriticalHits<0 || m.Reloads<0 || m.BurstCasts<0)
                    || !double.IsFinite(run.Members.Sum(m=>m.Damage))
                    || Math.Abs(run.TeamDamage-run.Members.Sum(m=>m.Damage))>Math.Max(1e-6,run.TeamDamage*1e-12)))throw new ArgumentException("invalid_run_summary");
                Execute(db,"INSERT OR IGNORE INTO batch_runs VALUES($id,$index,$attempt,$payload,$error)",("$id",id),("$index",row.Index),("$attempt",attempt),
                    ("$payload",row.Summary is null?null:Wire.Serialize(row.Summary)),("$error",row.ErrorCode));
            }
            tx.Commit();}
    }
    public void Finish(string id,int attempt,bool cancelled,string? error=null)
    {lock(gate){var batch=Read(id).Status;if(batch.Attempt!=attempt)return;var state=cancelled||batch.State=="cancelling"?"cancelled":batch.Valid==batch.Requested?"completed":"failed";
        using var db=Open();Execute(db,"UPDATE experiments SET state=$state,error=$error WHERE id=$id AND attempt=$attempt",("$id",id),("$attempt",attempt),("$state",state),("$error",error));}}
    public IReadOnlyList<RunSummary> Results(string id,int offset=0,int limit=100)
    {if(offset<0||limit is <1 or >1000)throw new ArgumentException("invalid_page");lock(gate){using var db=Open();using var c=Command(db,"SELECT payload FROM batch_runs WHERE batch=$id AND payload IS NOT NULL ORDER BY idx LIMIT $limit OFFSET $offset",("$id",id),("$limit",limit),("$offset",offset));
        using var r=c.ExecuteReader();var rows=new List<RunSummary>();while(r.Read())rows.Add(Wire.Read<RunSummary>(r.GetString(0)));return rows;}}
    public IEnumerable<RunSummary> AllResults(string id)
    {for(int offset=0;;offset+=1000){var page=Results(id,offset,1000);foreach(var row in page)yield return row;if(page.Count<1000)yield break;}}
    public (BatchStatus Batch,IReadOnlyList<RunSummary> Runs) AnalysisSnapshot(string id)
    {
        lock(gate){var batch=Read(id).Status;using var db=Open();using var command=Command(db,"SELECT payload FROM batch_runs WHERE batch=$id AND payload IS NOT NULL ORDER BY idx",("$id",id));
            using var reader=command.ExecuteReader();var rows=new List<RunSummary>(batch.Valid);while(reader.Read())rows.Add(Wire.Read<RunSummary>(reader.GetString(0)));return(batch,rows);}
    }
}
