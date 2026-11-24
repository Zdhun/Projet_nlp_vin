import { useEffect, useRef, useState } from "react";
import type { Options, PlotFigure, RecommendationAnalysis } from "../types";

const number = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

interface AnalysisChartsProps {
  analysis: RecommendationAnalysis;
  blocks: Options["blocks"];
}

export function AnalysisCharts({ analysis, blocks }: AnalysisChartsProps) {
  const { radar, ranking, heatmap, ranked_wines: wines, sentences } = analysis;

  return (
    <section className="charts" aria-labelledby="charts-title">
      <h2 id="charts-title" className="charts__title">Comparer les résultats</h2>
      <div className="charts__grid">
        <figure className="chart">
          <figcaption>
            <h3>Votre profil et le premier vin</h3>
            <p>Similarité cosinus par famille de goûts.</p>
          </figcaption>
          <Plot figure={radar} />
        </figure>

        <figure className="chart">
          <figcaption>
            <h3>{wines.length > 1 ? `Scores des ${wines.length} premiers vins` : "Score du vin classé"}</h3>
            <p>Score sur 100 parmi les vins retenus.</p>
          </figcaption>
          <Plot figure={ranking} />
          <details className="chart__details">
            <summary>Voir les vins et leurs scores</summary>
            <ol className="chart__ranking">
              {wines.map((wine, index) => (
                <li key={index}>
                  <span>{wine.title}</span>
                  <strong>{Math.round(wine.score * 100)} / 100</strong>
                </li>
              ))}
            </ol>
          </details>
        </figure>

        {heatmap && (
          <figure className="chart chart--wide">
            <figcaption>
              <h3>Vos phrases par famille de goûts</h3>
              <p>Chaque case mesure la proximité d’une phrase avec une famille, de −1 à 1.</p>
            </figcaption>
            <div className="chart__scroll">
              <Plot figure={heatmap} />
            </div>
            <details className="chart__details">
              <summary>Lire les phrases et leurs similarités</summary>
              <ol className="chart__sentences">
                {sentences.map((sentence, index) => (
                  <li key={index}>
                    <p>{sentence.text}</p>
                    <dl>
                      {blocks.map((block) => (
                        <div key={block.id}>
                          <dt>{block.name}</dt>
                          <dd>{number.format(sentence.scores[block.id])}</dd>
                        </div>
                      ))}
                    </dl>
                  </li>
                ))}
              </ol>
            </details>
          </figure>
        )}
      </div>
    </section>
  );
}

function Plot({ figure }: { figure: PlotFigure }) {
  const host = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!host.current) return;
    // Un nœud par montage évite de partager un graphique entre deux effets React.
    const plot = document.createElement("div");
    host.current.appendChild(plot);
    let cancelled = false;
    let dispose: (() => void) | undefined;

    void import("plotly.js-dist-min").then(async ({ default: Plotly }) => {
      if (cancelled) return;
      await Plotly.newPlot(plot, figure.data, figure.layout, {
        responsive: true,
        displayModeBar: false,
        displaylogo: false,
      });
      if (cancelled) {
        Plotly.purge(plot);
      } else {
        dispose = () => { Plotly.purge(plot); };
      }
    }).catch(() => {
      if (!cancelled) setFailed(true);
    });

    return () => {
      cancelled = true;
      dispose?.();
      plot.remove();
    };
  }, [figure]);

  return (
    <>
      <div ref={host} className="chart__plot" aria-hidden="true" />
      {failed && <p role="status">Le graphique n’a pas pu être chargé.</p>}
    </>
  );
}
