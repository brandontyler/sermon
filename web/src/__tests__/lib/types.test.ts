import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  CATEGORY_WEIGHTS,
  scoreColor,
  scoreBgColor,
  normalizeUrl,
} from "@/lib/types";

describe("scoreColor", () => {
  it("returns green for 74+", () => {
    expect(scoreColor(74)).toBe("text-green-500");
    expect(scoreColor(100)).toBe("text-green-500");
  });
  it("returns yellow for 60-73", () => {
    expect(scoreColor(60)).toBe("text-yellow-500");
    expect(scoreColor(73)).toBe("text-yellow-500");
  });
  it("returns red for below 60", () => {
    expect(scoreColor(59)).toBe("text-red-500");
    expect(scoreColor(0)).toBe("text-red-500");
  });
});

describe("scoreBgColor", () => {
  it("returns green for 74+", () => {
    expect(scoreBgColor(74)).toBe("bg-green-500");
  });
  it("returns yellow for 60-73", () => {
    expect(scoreBgColor(60)).toBe("bg-yellow-500");
  });
  it("returns red for below 60", () => {
    expect(scoreBgColor(0)).toBe("bg-red-500");
  });
});

describe("CATEGORY_LABELS", () => {
  it("has 8 categories", () => {
    expect(Object.keys(CATEGORY_LABELS)).toHaveLength(8);
  });
  it("has human-readable labels", () => {
    expect(CATEGORY_LABELS.biblicalAccuracy).toBe("Biblical Accuracy");
    expect(CATEGORY_LABELS.emotionalRange).toBe("Emotional Range");
  });
});

describe("CATEGORY_ORDER", () => {
  it("has 8 entries", () => {
    expect(CATEGORY_ORDER).toHaveLength(8);
  });
  it("starts with highest weight", () => {
    expect(CATEGORY_ORDER[0]).toBe("biblicalAccuracy");
    expect(CATEGORY_ORDER[1]).toBe("timeInTheWord");
  });
  it("ends with lowest weight", () => {
    expect(CATEGORY_ORDER[7]).toBe("emotionalRange");
  });
});

describe("normalizeUrl", () => {
  it("returns https URL unchanged", () => {
    expect(normalizeUrl("https://example.com")).toBe("https://example.com");
  });

  it("returns http URL unchanged", () => {
    expect(normalizeUrl("http://example.com")).toBe("http://example.com");
  });

  it("prepends https:// to bare domain", () => {
    expect(normalizeUrl("example.com")).toBe("https://example.com");
  });

  it("prepends https:// to www domain", () => {
    expect(normalizeUrl("www.example.com")).toBe("https://www.example.com");
  });

  it("returns empty string unchanged", () => {
    expect(normalizeUrl("")).toBe("");
  });
});
