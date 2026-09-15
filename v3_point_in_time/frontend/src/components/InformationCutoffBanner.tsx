export function InformationCutoffBanner({ cutoff }: { cutoff: string }) {
  return (
    <div className="cutoff-banner">
      INFORMATION CUTOFF: <strong>{cutoff}</strong> — everything in the panels below was defensibly known no later than this timestamp.
      Anything observed after it is separately labelled <span className="later-tag" style={{ marginLeft: 4 }}>OBSERVED LATER</span>.
    </div>
  );
}
