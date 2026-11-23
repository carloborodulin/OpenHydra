/** What a bar counts, and how to write its value. */
export interface Measure {
  /** The series name in the tooltip and the table header, for example "Victims". */
  name: string;
  /** Formats one value for the tooltip and the table. */
  format: (v: number) => string;
  /** Formats an axis tick (short form). */
  axis: (v: number) => string;
}

const full = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const usdCents = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const usdCompact = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

export const count = (name: string): Measure => ({
  name,
  format: (v) => full.format(v),
  axis: (v) => compact.format(v),
});

export const dollars = (name: string): Measure => ({
  name,
  format: (v) => (Math.abs(v) < 10 ? usdCents.format(v) : usd.format(v)),
  axis: (v) => (v === 0 ? "$0" : Math.abs(v) < 10 ? usdCents.format(v) : usdCompact.format(v)),
});

export const ARRESTS = count("Arrests");

/** The measure of one breakdown dimension of a domain. */
export function measureFor(domain: string, key: string): Measure {
  if (domain === "property") {
    if (key.endsWith("average_value")) return dollars("Average value");
    if (key === "stolen_value") return dollars("Stolen value");
    if (key === "recovered_value") return dollars("Recovered value");
    return count("Offenses");
  }
  if (domain === "nibrs-estimation") return count("Estimated count");
  if (key.startsWith("victim")) return count("Victims");
  if (key.startsWith("offender")) return count("Offenders");
  if (domain === "homicide") return count("Victims");
  if (domain === "hate-crime") return count("Incidents");
  return count("Count");
}
