using System.Runtime.CompilerServices;
[assembly: InternalsVisibleTo("Nikke.Compute.Tests")]
namespace Nikke.Compute;

// Each measurement receives its own reservation, even when cold warmup was interrupted.
internal sealed record TuningBudget(TimeSpan Warmup, TimeSpan Candidate)
{
    public static TuningBudget Default {get;}=new(TimeSpan.FromSeconds(2),TimeSpan.FromSeconds(24));
    public double TotalMilliseconds(int candidates)=>Warmup.TotalMilliseconds+candidates*Candidate.TotalMilliseconds;
}
