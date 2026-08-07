
function renderInlineBold(line, lineKey) {
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={`${lineKey}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export function renderInlineMarkdown(text) {
  if (!text) return text;
  const lines = String(text).split("\n");

  return lines.map((line, i) => {
    const headingMatch = line.match(/^#{1,6}\s+(.*)$/);
    const body = headingMatch ? headingMatch[1] : line;
    const rendered = headingMatch ? (
      <strong>{renderInlineBold(body, i)}</strong>
    ) : (
      renderInlineBold(body, i)
    );

    return (
      <span key={i}>
        {rendered}
        {i < lines.length - 1 && <br />}
      </span>
    );
  });
}