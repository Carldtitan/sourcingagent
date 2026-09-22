/** The red trace that runs through a primary action, borrowed from the
 *  force diagram so a button reads as part of the same structure. */
export function Trace() {
  return (
    <svg width="26" height="10" viewBox="0 0 26 10" aria-hidden="true">
      <polyline
        className="trace"
        points="0,7 6,7 10,3 16,3 20,6 26,6"
        fill="none"
        strokeWidth="1.4"
      />
      <circle cx="26" cy="6" r="1.6" fill="currentColor" className="trace" />
    </svg>
  );
}
