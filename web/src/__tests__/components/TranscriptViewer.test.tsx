import { render, screen } from "@testing-library/react";
import TranscriptViewer from "@/components/TranscriptViewer";
import { TranscriptSegment } from "@/lib/types";

const segments: TranscriptSegment[] = [
  { start: 0, end: 10, text: "The morning text is Romans 8:28", type: "scripture" },
  { start: 10, end: 20, text: "This means God works for good", type: "teaching" },
  { start: 20, end: 30, text: "Go apply this to your life", type: "application" },
  { start: 30, end: 40, text: "I was at a construction site", type: "anecdote" },
];

describe("TranscriptViewer", () => {
  it("renders all segments", () => {
    render(<TranscriptViewer segments={segments} />);
    expect(screen.getByText(/morning text/)).toBeInTheDocument();
    expect(screen.getByText(/God works for good/)).toBeInTheDocument();
    expect(screen.getByText(/apply this/)).toBeInTheDocument();
    expect(screen.getByText(/construction site/)).toBeInTheDocument();
  });

  it("renders legend items", () => {
    render(<TranscriptViewer segments={segments} />);
    expect(screen.getByText("Scripture")).toBeInTheDocument();
    expect(screen.getByText("Teaching")).toBeInTheDocument();
    expect(screen.getByText("Application")).toBeInTheDocument();
    expect(screen.getByText("Anecdote")).toBeInTheDocument();
  });

  it("bolds scripture references", () => {
    render(<TranscriptViewer segments={segments} />);
    const bold = screen.getByText(/Romans/);
    expect(bold.tagName).toBe("STRONG");
  });

  it("handles segments with no scripture references", () => {
    const plain: TranscriptSegment[] = [
      { start: 0, end: 10, text: "No references here", type: "teaching" },
    ];
    render(<TranscriptViewer segments={plain} />);
    expect(screen.getByText("No references here")).toBeInTheDocument();
  });

  it("handles empty segments array", () => {
    const { container } = render(<TranscriptViewer segments={[]} />);
    expect(container.querySelector(".overflow-y-auto")?.children).toHaveLength(0);
  });
});
