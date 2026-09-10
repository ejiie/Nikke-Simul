namespace Nikke.Contracts;

// One latest error notification, not a placeholder account or an unbounded failure history.
public sealed record ConnectionFailureNotice(DateTimeOffset OccurredAt, string Code, string Message);
