import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import SermonDetailClient from "@/components/SermonDetail";

// Mock ResizeObserver (needed by Recharts)
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

// Mock next/navigation
const SERMON_ID = "12345678-1234-1234-1234-123456789012";
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useParams: () => ({ id: SERMON_ID }),
  useRouter: () => ({ push: mockPush }),
}));

// Set URL for ID resolution (jsdom supports history.pushState)
beforeEach(() => {
  window.history.pushState({}, "", `/sermons/${SERMON_ID}`);
});

const COMPLETE_SERMON = {
  id: SERMON_ID,
  title: "Test Sermon",
  pastor: "Pastor Test",
  date: "2026-03-22",
  duration: 1800,
  status: "complete",
  sermonType: "expository",
  compositePsr: 82.5,
  summary: "A solid expository sermon.",
  categories: {
    biblicalAccuracy: { score: 90, weight: 25, reasoning: "Strong exegesis" },
    timeInTheWord: { score: 85, weight: 20, reasoning: "Dense biblical content" },
    passageFocus: { score: 80, weight: 10, reasoning: "Stayed on passage" },
    clarity: { score: 75, weight: 10, reasoning: "Clear structure" },
    engagement: { score: 70, weight: 10, reasoning: "Good illustrations" },
    application: { score: 65, weight: 10, reasoning: "Some takeaways" },
    delivery: { score: 78, weight: 10, reasoning: "Confident delivery" },
    emotionalRange: { score: 72, weight: 5, reasoning: "Good variation" },
  },
  strengths: ["Strong biblical grounding", "Clear structure"],
  improvements: ["More specific application"],
  transcript: { fullText: "Test transcript text", segments: [{ start: 0, end: 10, text: "Hello", type: "teaching" }] },
  error: null,
  failedAt: null,
  blobUrl: null,
  filename: null,
  wpmFlag: false,
  audioMetrics: null,
  classificationConfidence: 90,
  normalizationApplied: "full",
  aiScore: 1,
  aiReasoning: "Clearly human",
  sermonSummary: { overview: "A test sermon", keyPoints: ["Point 1"] },
};

function mockFetch(data: any, status = 200) {
  global.fetch = jest.fn((url: string) => {
    if (typeof url === "string" && url.includes("/api/churches")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
    }
    return Promise.resolve({ ok: status === 200, status, json: () => Promise.resolve(data) });
  }) as any;
}

describe("SermonDetail", () => {
  afterEach(() => jest.restoreAllMocks());

  it("shows loading state initially", () => {
    global.fetch = jest.fn(() => new Promise(() => {})); // never resolves
    render(<SermonDetailClient />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows 'Sermon not found' for 404", async () => {
    mockFetch({}, 404);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Sermon not found.")).toBeInTheDocument());
  });

  it("renders complete sermon with score gauge", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Test Sermon")).toBeInTheDocument());
    expect(screen.getByText("/100")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /PSR score/ })).toBeInTheDocument();
  });

  it("renders all 8 category cards", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Biblical Accuracy")).toBeInTheDocument());
    expect(screen.getByText("Time in the Word")).toBeInTheDocument();
    expect(screen.getByText("Passage Focus")).toBeInTheDocument();
    expect(screen.getByText("Clarity")).toBeInTheDocument();
    expect(screen.getByText("Engagement")).toBeInTheDocument();
    // "Application" appears in both category card and transcript legend
    expect(screen.getAllByText("Application").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Delivery")).toBeInTheDocument();
    expect(screen.getByText("Emotional Range")).toBeInTheDocument();
    // Verify all 8 "View reasoning" buttons exist
    expect(screen.getAllByText("▸ View reasoning")).toHaveLength(8);
  });

  it("toggles reasoning on category card click", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Biblical Accuracy")).toBeInTheDocument());

    const viewBtns = screen.getAllByText("▸ View reasoning");
    expect(viewBtns.length).toBe(8);

    fireEvent.click(viewBtns[0]);
    expect(screen.getByText("Strong exegesis")).toBeInTheDocument();
    expect(screen.getByText("▾ Hide reasoning")).toBeInTheDocument();

    fireEvent.click(screen.getByText("▾ Hide reasoning"));
    expect(screen.queryByText("Strong exegesis")).not.toBeInTheDocument();
  });

  it("renders strengths and improvements", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Strengths")).toBeInTheDocument());
    expect(screen.getByText("Strong biblical grounding")).toBeInTheDocument();
    expect(screen.getByText("Areas to Improve")).toBeInTheDocument();
    expect(screen.getByText("More specific application")).toBeInTheDocument();
  });

  it("renders AI stoplight for human score", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText(/Human/)).toBeInTheDocument());
    expect(screen.getByText(/No AI detected/)).toBeInTheDocument();
  });

  it("renders processing state", async () => {
    mockFetch({ ...COMPLETE_SERMON, status: "processing", categories: null });
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Analyzing sermon...")).toBeInTheDocument());
    expect(screen.getByText(/5 minutes/)).toBeInTheDocument();
  });

  it("renders failed state with error", async () => {
    mockFetch({ ...COMPLETE_SERMON, status: "failed", error: "LLM timeout", categories: null });
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText(/Something went wrong/)).toBeInTheDocument());
    expect(screen.getByText(/LLM timeout/)).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("renders back to sermons link", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("← Back to sermons")).toBeInTheDocument());
  });

  it("renders sermon metadata", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("Pastor Test")).toBeInTheDocument());
    expect(screen.getByText("30 min", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("expository")).toBeInTheDocument();
  });

  it("renders summary text", async () => {
    mockFetch(COMPLETE_SERMON);
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("A solid expository sermon.")).toBeInTheDocument());
  });

  it("renders bonus when present", async () => {
    mockFetch({ ...COMPLETE_SERMON, bonus: 5.0, totalScore: 87.5 });
    render(<SermonDetailClient />);
    await waitFor(() => expect(screen.getByText("+5.0 bonus")).toBeInTheDocument());
    expect(screen.getByText("87.5")).toBeInTheDocument();
  });
});
