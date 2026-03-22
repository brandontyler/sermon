import { render, screen } from "@testing-library/react";
import ScoreGauge from "@/components/ScoreGauge";

describe("ScoreGauge", () => {
  it("renders the score number with one decimal", () => {
    render(<ScoreGauge score={83} />);
    expect(screen.getByText("83.0")).toBeInTheDocument();
    expect(screen.getByText("/100")).toBeInTheDocument();
  });

  it("renders aria-label with score", () => {
    render(<ScoreGauge score={75} />);
    expect(screen.getByRole("img")).toHaveAttribute(
      "aria-label",
      "PSR score: 75.0 out of 100"
    );
  });

  it("uses green color for score >= 74", () => {
    render(<ScoreGauge score={85} />);
    const num = screen.getByText("85.0");
    expect(num).toHaveStyle({ color: "#22c55e" });
  });

  it("uses yellow color for score 60-73", () => {
    render(<ScoreGauge score={65} />);
    const num = screen.getByText("65.0");
    expect(num).toHaveStyle({ color: "#eab308" });
  });

  it("uses red color for score < 60", () => {
    render(<ScoreGauge score={30} />);
    const num = screen.getByText("30.0");
    expect(num).toHaveStyle({ color: "#ef4444" });
  });

  it("renders SVG with background arc", () => {
    const { container } = render(<ScoreGauge score={50} />);
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBeGreaterThanOrEqual(1);
  });

  it("renders no score arc when score is 0", () => {
    const { container } = render(<ScoreGauge score={0} />);
    const paths = container.querySelectorAll("path");
    // Only background arc, no score arc
    expect(paths).toHaveLength(1);
  });

  it("renders decimal scores as-is", () => {
    render(<ScoreGauge score={82.7} />);
    expect(screen.getByText("82.7")).toBeInTheDocument();
  });
});
