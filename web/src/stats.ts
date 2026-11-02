export interface Bucket {
  start: number;
  end: number;
  count: number;
}

/** Split values into `bucketCount` equal-width buckets between their min and max. */
export function histogram(values: number[], bucketCount = 10): Bucket[] {
  const finite = values.filter((value) => Number.isFinite(value));
  if (finite.length === 0 || bucketCount <= 0) return [];
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) return [{ start: min, end: max, count: finite.length }];
  const width = (max - min) / bucketCount;
  const buckets: Bucket[] = Array.from({ length: bucketCount }, (_, index) => ({
    start: min + index * width,
    end: index === bucketCount - 1 ? max : min + (index + 1) * width,
    count: 0,
  }));
  for (const value of finite) {
    const index = Math.min(bucketCount - 1, Math.floor((value - min) / width));
    const bucket = buckets[index];
    if (bucket) bucket.count += 1;
  }
  return buckets;
}

/** Linear-interpolated percentile (q in [0, 100]), matching the Python analysis module. */
export function percentile(values: number[], q: number): number {
  if (values.length === 0) return 0;
  if (q < 0 || q > 100) throw new RangeError("q must be in [0, 100]");
  const ordered = [...values].sort((a, b) => a - b);
  const rank = (q / 100) * (ordered.length - 1);
  const low = Math.floor(rank);
  const high = Math.min(low + 1, ordered.length - 1);
  const lowValue = ordered[low] ?? 0;
  const highValue = ordered[high] ?? lowValue;
  return lowValue + (highValue - lowValue) * (rank - low);
}

/** Round a chart maximum up to 1, 2, 2.5, 5, or 10 times a power of ten. */
export function niceMax(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  for (const factor of [1, 2, 2.5, 5, 10]) {
    if (value <= factor * power + power * 1e-9) return factor * power;
  }
  return 10 * power;
}

export interface Bar {
  label: string;
  value: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BarChartGeometry {
  bars: Bar[];
  max: number;
}

/** Compute vertical bar positions for an SVG chart area of the given size. */
export function barGeometry(
  data: Array<{ label: string; value: number }>,
  width: number,
  height: number,
  gap = 0.25,
): BarChartGeometry {
  const max = niceMax(Math.max(0, ...data.map((item) => item.value)));
  if (data.length === 0) return { bars: [], max };
  const slot = width / data.length;
  const barWidth = slot * (1 - gap);
  const bars = data.map((item, index) => {
    const barHeight = (Math.max(0, item.value) / max) * height;
    return {
      label: item.label,
      value: item.value,
      x: index * slot + (slot - barWidth) / 2,
      y: height - barHeight,
      width: barWidth,
      height: barHeight,
    };
  });
  return { bars, max };
}
