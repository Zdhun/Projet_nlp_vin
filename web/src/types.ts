// Types partagés entre l'interface et l'API Python (api/main.py).

import type { Data, Layout } from "plotly.js";

export type BlockId = "fruit" | "spice_oak" | "floral_mineral" | "structure" | "pairing";
export type YesNo = "yes" | "no";
export type WineColor = "red" | "white" | "rose" | "sparkling" | "dessert";

/** Réponses du questionnaire, envoyées telles quelles à POST /api/recommend. */
export interface Answers {
  description: string;
  liked_wine_reason: string;
  food_or_occasion: string;
  color: string;
  intensity_likert: number | null;
  fruity_likert: number | null;
  woody_likert: number | null;
  sweetness_likert: number | null;
  acidity_likert: number | null;
  oak_tasted: YesNo | null;
  oak_liked: YesNo | null;
  aromas: string[];
  countries: string[];
  max_price: number;
}

export interface Option {
  id: string;
  label: string;
}

export interface Options {
  blocks: { id: BlockId; name: string }[];
  aromas: Option[];
  colors: (Option & { key: WineColor | "any" })[];
  countries: (Option & { count: number })[];
  price: { min: number; max: number; median: number };
  wine_count: number;
}

export interface Wine {
  wine_id: string;
  title: string;
  winery: string;
  variety: string;
  color: WineColor;
  country: string;
  country_fr: string;
  province: string | null;
  region: string | null;
  price: number;
  points: number;
  description: string;
  foods_fr: string[];
}

export interface Recommendation {
  rank: number;
  score: number;
  breakdown: {
    semantic_norm: number;
    block_affinity_norm: number;
    preferences_norm: number;
    semantic_raw: number;
  };
  wine: Wine;
  user_blocks: Record<BlockId, number>;
  wine_blocks: Record<BlockId, number>;
  reasons: { block: BlockId | null; label: string; similarity: number }[];
  explanation: string;
}

export interface PlotFigure {
  data: Data[];
  layout: Partial<Layout>;
}

export interface RecommendationAnalysis {
  radar: PlotFigure;
  ranking: PlotFigure;
  heatmap: PlotFigure | null;
  ranked_wines: { title: string; score: number }[];
  sentences: { text: string; scores: Record<BlockId, number> }[];
}

export interface RecommendResponse {
  id: string;
  results: Recommendation[];
  analysis: RecommendationAnalysis;
}
