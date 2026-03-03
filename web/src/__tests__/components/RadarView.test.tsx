import { render } from "@testing-library/react";
import RadarView from "@/components/RadarView";
import { CategoryScore } from "@/lib/types";

// Mock recharts since it doesn't render in jsdom
jest.mock("recharts", () => ({
  Radar: ({ dataKey }: { dataKey: string }) => <div data-testid={`radar-${dataKey}`} />,
  RadarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: () => <div data-testid="polar-angle-axis" />,
  PolarRadiusAxis: () => <div data-testid="polar-radius-axis" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: () => <div data-testid="tooltip" />,
}));

const categories: Record<string, CategoryScore> = {
  biblicalAccuracy: { score: 90, weight: 25, reasoning: "" },
  timeInTheWord: { score: 85, weight: 20, reasoning: "" },
  passageFocus: { score: 80, weight: 10, reasoning: "" },
  clarity: { score: 82, weight: 10, reasoning: "" },
  engagement: { score: 88, weight: 10, reasoning: "" },
  application: { score: 75, weight: 10, reasoning: "" },
  delivery: { score: 78, weight: 10, reasoning: "" },
  emotionalRange: { score: 70, weight: 5, reasoning: "" },
};

describe("RadarView", () => {
  it("renders radar chart", () => {
    const { getByTestId } = render(<RadarView categories={categories} />);
    expect(getByTestId("radar-chart")).toBeInTheDocument();
  });

  it("renders radar data layer", () => {
    const { getByTestId } = render(<RadarView categories={categories} />);
    expect(getByTestId("radar-score")).toBeInTheDocument();
  });

  it("handles missing categories gracefully", () => {
    const partial: Record<string, CategoryScore> = {
      biblicalAccuracy: { score: 90, weight: 25, reasoning: "" },
    };
    const { getByTestId } = render(<RadarView categories={partial} />);
    expect(getByTestId("radar-chart")).toBeInTheDocument();
  });
});
