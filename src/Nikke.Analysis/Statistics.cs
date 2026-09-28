namespace Nikke.Analysis;

public sealed record Interval(double Lower, double Upper, double Confidence, string Method);
public sealed record Distribution(long N, double? Mean, double? SampleSd, Interval? MeanCi,
    double? Median, double? P5, double? P95, long? CutSuccesses, double? CutProbability,
    Interval? CutCi, string Unit, string QuantileMethod = "Hyndman-Fan type 7",
    string Inference = "fixed-N independent runs; normal-model t CI, asymptotic for nonnormal data; not model-error coverage");

/// <summary>Shifted Welford/Chan moments. The origin avoids loss of small differences at large offsets.</summary>
public sealed class Moments
{
    public long N { get; private set; }
    private double origin, offset, m2;
    public double Mean => N == 0 ? throw new InvalidOperationException("No samples") : origin + offset;
    public double? Variance => N < 2 ? null : Math.Max(0, m2 / (N - 1));
    public void Add(double value)
    {
        if (!double.IsFinite(value) || Math.Abs(value) > 9e15) throw new ArgumentOutOfRangeException(nameof(value));
        if (N == 0) { origin = value; N = 1; return; }
        var delta = (value - origin) - offset;
        N = checked(N + 1);
        offset += delta / N;
        m2 += delta * ((value - origin) - offset);
    }
    public void Merge(Moments other)
    {
        if (ReferenceEquals(this, other)) throw new ArgumentException("Cannot merge self");
        if (other.N == 0) return;
        if (N == 0) { origin = other.origin; offset = other.offset; m2 = other.m2; N = other.N; return; }
        var n = checked(N + other.N);
        var delta = (other.origin - origin) + (other.offset - offset);
        m2 += other.m2 + delta * delta * ((double)N / n) * other.N;
        offset += delta * ((double)other.N / n);
        N = n;
    }
}

/// <summary>Exact quantiles have explicit O(N) storage; no silent sketch or discarded tail.</summary>
public sealed class DistributionAccumulator(int capacity = 50000, double? cut = null, string unit = "damage")
{
    private readonly List<double> values = [];
    private readonly Moments moments = new();
    public int N => values.Count;
    public void Add(double value)
    {
        if (capacity < 1 || N >= capacity) throw new InvalidOperationException("Exact quantile sample capacity exceeded");
        if (cut is { } c && !double.IsFinite(c)) throw new ArgumentException("Invalid cut");
        moments.Add(value);
        values.Add(value);
    }
    public void Merge(DistributionAccumulator other)
    {
        if (ReferenceEquals(this, other) || cut != other.Cut || unit != other.Unit || N + other.N > capacity)
            throw new ArgumentException("Incompatible or oversized accumulator merge");
        moments.Merge(other.moments);
        values.AddRange(other.values);
    }
    private double? Cut => cut;
    internal double? Threshold => cut;
    private string Unit => unit;
    public Distribution Snapshot()
    {
        var ordered = values.Order().ToArray();
        double? Q(double p)
        {
            if (N == 0) return null;
            var h = (N - 1) * p;
            int lo = (int)h, hi = Math.Min(lo + 1, N - 1);
            return ordered[lo] + (ordered[hi] - ordered[lo]) * (h - lo);
        }
        var mean = N > 0 ? moments.Mean : (double?)null;
        var sd = moments.Variance is { } v ? Math.Sqrt(v) : (double?)null;
        Interval? ci = sd is { } s ? Inference.MeanInterval(mean!.Value, s, N) : null;
        long? successes = cut is { } c ? values.LongCount(x => x > c) : null;
        double? probability = successes is { } k && N > 0 ? (double)k / N : null;
        return new(N, mean, sd, ci, Q(.5), Q(.05), Q(.95), successes, probability,
            successes is { } count && N > 0 ? Inference.Wilson(count, N) : null, unit);
    }
}

public sealed record MeanDifference(double? Difference, Interval? Ci, double? DegreesOfFreedom,
    string Decision, string Design = "independent samples; Welch-Satterthwaite; Bonferroni family adjustment");
public sealed record SampleSizePlan(long? RequiredN, bool ExceedsBudget, string Status,
    int PilotTarget = 1000, int MainTarget = 10000, int SustainedTarget = 50000);

public static class Inference
{
    public static Interval MeanInterval(double mean, double sd, long n)
    {
        if (n < 2 || !double.IsFinite(mean) || !double.IsFinite(sd) || sd < 0) throw new ArgumentException("Invalid moments");
        var half = StudentCritical(.975, n - 1) * sd / Math.Sqrt(n);
        return new(mean - half, mean + half, .95, "Student t; fixed N");
    }
    public static Interval Wilson(long successes, long n)
    {
        if (n < 1 || successes < 0 || successes > n) throw new ArgumentException("Invalid binomial count");
        const double z = 1.959963984540054;
        double p = (double)successes / n, z2 = z * z, d = 1 + z2 / n;
        var center = (p + z2 / (2 * n)) / d;
        var half = z * Math.Sqrt(p * (1 - p) / n + z2 / (4.0 * n * n)) / d;
        return new(Math.Max(0, center - half), Math.Min(1, center + half), .95, "Wilson score; strict damage > cut");
    }
    public static MeanDifference Compare(Distribution baseline, Distribution candidate, int familySize = 1)
    {
        if (familySize < 1 || familySize > 10000 || baseline.Unit != candidate.Unit) throw new ArgumentException("Invalid comparison family/unit");
        var difference = candidate.Mean - baseline.Mean;
        if (baseline.N < 2 || candidate.N < 2 || baseline.SampleSd is null || candidate.SampleSd is null)
            return new(difference, null, null, "insufficient_samples");
        double a = Math.Pow(baseline.SampleSd.Value, 2) / baseline.N, b = Math.Pow(candidate.SampleSd.Value, 2) / candidate.N;
        if (a + b == 0)
            return new(difference, null, null, "zero_variance_unresolved");
        double df = (a + b) * (a + b) / (a * a / (baseline.N - 1) + b * b / (candidate.N - 1));
        var confidence = 1 - .05 / familySize;
        var half = StudentCritical(1 - .025 / familySize, df) * Math.Sqrt(a + b);
        var ci = new Interval(difference!.Value - half, difference.Value + half, confidence, "Welch t; Bonferroni");
        return new(difference, ci, df, ci.Lower > 0 ? "model_improvement" : ci.Upper < 0 ? "model_worse" : "unresolved");
    }
    public static SampleSizePlan Plan(Distribution pilot, double absoluteHalfWidth, long budget = 50000)
    {
        if (!double.IsFinite(absoluteHalfWidth) || absoluteHalfWidth <= 0 || budget < 2) throw new ArgumentException("Invalid precision/budget");
        if (pilot.N < 2 || pilot.SampleSd is null) return new(null, false, "insufficient_pilot");
        if (pilot.SampleSd == 0) return new(null, false, "zero_pilot_variance_not_precision_proof");
        double estimate = Math.Pow(StudentCritical(.975, pilot.N - 1) * pilot.SampleSd.Value / absoluteHalfWidth, 2);
        if (!double.IsFinite(estimate) || estimate >= long.MaxValue) return new(null, true, "required_n_exceeds_integer_range");
        long n = Math.Max(2, (long)Math.Ceiling(estimate));
        return new(n, n > budget, "pilot_based_planning_estimate; freeze N before independent final runs; no optional-stopping guarantee");
    }

    // Invert the regularized incomplete beta form of the Student t CDF.
    public static double StudentCritical(double probability, double df)
    {
        if (probability <= .5 || probability >= 1 || !double.IsFinite(df) || df <= 0) throw new ArgumentException("Invalid t quantile");
        double lo = 0, hi = 1, tail = 1 - probability;
        double UpperTail(double t) => .5 * Beta(df / (df + t * t), df / 2, .5);
        while (UpperTail(hi) > tail) { hi *= 2; if (hi > 1e12) throw new ArithmeticException("t quantile range"); }
        for (int i = 0; i < 100; i++) { double mid = lo + (hi - lo) / 2; if (UpperTail(mid) > tail) lo = mid; else hi = mid; }
        return (lo + hi) / 2;
    }
    private static double LogGamma(double x)
    {
        double[] c = [676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059,
            12.507343278686905, -.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
        x -= 1;
        double sum = .99999999999980993;
        for (int i = 0; i < c.Length; i++) sum += c[i] / (x + i + 1);
        double t = x + 7.5;
        return .9189385332046727 + (x + .5) * Math.Log(t) - t + Math.Log(sum);
    }
    private static double Beta(double x, double a, double b)
    {
        if (x <= 0) return 0;
        if (x >= 1) return 1;
        var front = Math.Exp(LogGamma(a + b) - LogGamma(a) - LogGamma(b) + a * Math.Log(x) + b * Math.Log(1 - x));
        return x < (a + 1) / (a + b + 2) ? front * Fraction(x, a, b) / a : 1 - front * Fraction(1 - x, b, a) / b;
    }
    private static double Fraction(double x, double a, double b)
    {
        static double Safe(double v) => Math.Abs(v) < 1e-300 ? Math.CopySign(1e-300, v) : v;
        double c = 1, d = 1 / Safe(1 - (a + b) * x / (a + 1)), h = d;
        for (int m = 1; m <= 10000; m++)
        {
            double aa = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m));
            d = 1 / Safe(1 + aa * d); c = Safe(1 + aa / c); h *= d * c;
            aa = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1));
            d = 1 / Safe(1 + aa * d); c = Safe(1 + aa / c);
            var delta = d * c; h *= delta;
            if (Math.Abs(delta - 1) < 3e-14) return h;
        }
        throw new ArithmeticException("Incomplete beta did not converge");
    }
}
