/** 270° arc gauge like Lighthouse */
export default function ScoreGauge({ score }: { score: number }) {
  const radius = 80;
  const stroke = 10;
  const cx = 100;
  const cy = 100;
  // 270° arc: starts at 135° (bottom-left), ends at 405° (bottom-right)
  const startAngle = 135;
  const endAngle = 405;
  const totalAngle = endAngle - startAngle;
  const scoreAngle = startAngle + (score / 100) * totalAngle;

  function polarToCartesian(angle: number) {
    const rad = (angle * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  }

  function arcPath(start: number, end: number) {
    const s = polarToCartesian(start);
    const e = polarToCartesian(end);
    const largeArc = end - start > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${largeArc} 1 ${e.x} ${e.y}`;
  }

  const color = score >= 70 ? "#22c55e" : score >= 50 ? "#eab308" : "#ef4444";

  return (
    <div className="relative w-[200px] h-[200px]" role="img" aria-label={`PSR score: ${Math.round(score)} out of 100`}>
      <svg viewBox="0 0 200 200" className="w-full h-full">
        {/* Background arc */}
        <path d={arcPath(startAngle, endAngle)} fill="none" stroke="#e5e7eb" strokeWidth={stroke} strokeLinecap="round" />
        {/* Score arc */}
        {score > 0 && (
          <path d={arcPath(startAngle, scoreAngle)} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-5xl font-bold" style={{ color }}>{Math.round(score)}</span>
        <span className="text-sm text-gray-400">/100</span>
      </div>
    </div>
  );
}
