import { apiUrl, API_BASE } from "@/lib/api";

describe("apiUrl", () => {
  it("prepends API_BASE to path", () => {
    expect(apiUrl("/api/sermons")).toBe(`${API_BASE}/api/sermons`);
  });

  it("handles path with no leading slash", () => {
    expect(apiUrl("api/sermons")).toBe(`${API_BASE}api/sermons`);
  });

  it("handles empty path", () => {
    expect(apiUrl("")).toBe(API_BASE);
  });
});
