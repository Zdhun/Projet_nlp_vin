import type { Answers, BlockId, Options, Recommendation, RecommendationAnalysis } from "../types";
import { AnalysisCharts } from "./AnalysisCharts";
import { Glass } from "./Glass";

const RANK_LABEL = ["Premier choix", "Deuxième choix", "Troisième choix"];
const RESULTS_TITLE = ["Votre vin.", "Vos deux vins.", "Vos trois vins."];

const COLOR_LABEL: Record<string, string> = {
  red: "Rouge",
  white: "Blanc",
  rose: "Rosé",
  sparkling: "Effervescent",
  dessert: "Doux",
};

/**
 * Les similarités cosinus du modèle restent entre ~0,3 et ~0,8 : on étire cette plage
 * pour que les écarts entre familles de goûts soient lisibles. Les valeurs brutes restent
 * consultables au survol.
 */
const stretch = (v: number) => Math.min(1, Math.max(0, (v - 0.3) / 0.5));
const pct = (v: number) => Math.round(v * 100);

interface ResultsProps {
  results: Recommendation[];
  analysis: RecommendationAnalysis;
  answers: Answers;
  options: Options;
  onEdit: () => void;
  onRestart: () => void;
}

export function Results({ results, analysis, answers, options, onEdit, onRestart }: ResultsProps) {
  const blockName = (id: BlockId | null) => options.blocks.find((b) => b.id === id)?.name ?? "";

  return (
    <main className="results">
      <header className="results__head">
        <h1 className="results__title">{RESULTS_TITLE[results.length - 1]}</h1>
        <blockquote className="results__query">« {answers.description.trim()} »</blockquote>
        <div className="results__actions">
          <button className="button button--secondary" onClick={onEdit}>
            Modifier mes réponses
          </button>
          <button className="button button--quiet" onClick={onRestart}>
            Recommencer
          </button>
        </div>
      </header>

      <AnalysisCharts analysis={analysis} blocks={options.blocks} />

      {results.map((r) => (
        <article key={r.wine.wine_id} className="wine" aria-labelledby={`wine-${r.wine.wine_id}`}>
          <div className="wine__visual">
            <Glass
              level={0.25 + r.score * 0.7}
              color={r.wine.color}
              bubbles={r.wine.color === "sparkling"}
              label={`Verre de vin ${COLOR_LABEL[r.wine.color]?.toLowerCase() ?? ""}`}
            />
            <p className="wine__score">
              <span className="wine__score-value">{pct(r.score)}</span>
              <span className="wine__score-unit">sur 100</span>
            </p>
            <p className="wine__score-note">Score relatif aux vins de votre budget et de votre couleur.</p>
          </div>

          <div className="wine__content">
            <p className="wine__rank">{RANK_LABEL[r.rank - 1]}</p>
            <h2 id={`wine-${r.wine.wine_id}`} className="wine__title">
              {r.wine.title}
            </h2>

            <dl className="facts">
              <div>
                <dt>Cépage</dt>
                <dd>{r.wine.variety}</dd>
              </div>
              <div>
                <dt>Origine</dt>
                <dd>{[r.wine.region, r.wine.country_fr].filter(Boolean).join(", ")}</dd>
              </div>
              <div>
                <dt>Prix</dt>
                <dd>{r.wine.price} $</dd>
              </div>
              <div>
                <dt>Note du critique</dt>
                <dd>{r.wine.points} / 100</dd>
              </div>
            </dl>

            <figure className="tasting">
              <blockquote lang="en">{r.wine.description}</blockquote>
              <figcaption>Note de dégustation Wine Enthusiast, en anglais</figcaption>
            </figure>

            <section className="why" aria-label="Pourquoi ce vin">
              <h3 className="why__title">Pourquoi ce vin</h3>
              <p className="why__explanation">{r.explanation}</p>
              <div className="split">
                <Meter label="Sens de votre description" value={r.breakdown.semantic_norm} />
                <Meter label="Profil de goût partagé" value={r.breakdown.block_affinity_norm} />
                <Meter label="Vos préférences cochées" value={r.breakdown.preferences_norm} />
              </div>

              {r.reasons.length > 0 && (
                <ul className="reasons">
                  {r.reasons.map((reason) => (
                    <li key={reason.label}>
                      <span className="reasons__label">{reason.label}</span>
                      <span className="reasons__block">{blockName(reason.block)}</span>
                    </li>
                  ))}
                </ul>
              )}

              <table className="profile">
                <caption>Proximité avec chaque famille de goûts</caption>
                <thead>
                  <tr>
                    <th scope="col">Famille</th>
                    <th scope="col">
                      <span className="legend legend--you" /> Vous
                    </th>
                    <th scope="col">
                      <span className="legend legend--wine" /> Ce vin
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {options.blocks.map((b) => (
                    <tr key={b.id}>
                      <th scope="row">{b.name}</th>
                      <td>
                        <Bar value={r.user_blocks[b.id]} tone="you" />
                      </td>
                      <td>
                        <Bar value={r.wine_blocks[b.id]} tone="wine" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {r.wine.foods_fr.length > 0 && (
              <section className="pairing" aria-label="Accords suggérés">
                <h3 className="why__title">À table avec</h3>
                <ul className="pairing__list">
                  {r.wine.foods_fr.map((food) => (
                    <li key={food}>{food}</li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </article>
      ))}

      <section className="method">
        <h2>Comment ce choix a été fait</h2>
        <p>
          Vos réponses écrites sont encodées par un modèle SBERT multilingue
          (paraphrase-multilingual-MiniLM-L12-v2), puis comparées par similarité cosinus aux notes
          de dégustation et à cinq familles de goûts. Le score combine le sens global (60 %), le
          profil par famille (30 %) et vos préférences cochées (10 %), après filtrage par budget
          et par couleur.
        </p>
      </section>
    </main>
  );
}

function Meter({ label, value }: { label: string; value: number }) {
  return (
    <div className="meter">
      <span className="meter__value">{pct(value)}</span>
      <span className="meter__label">{label}</span>
      <div className="meter__track" aria-hidden="true">
        <div className="meter__fill" style={{ transform: `scaleX(${value})` }} />
      </div>
    </div>
  );
}

function Bar({ value, tone }: { value: number; tone: "you" | "wine" }) {
  return (
    <div className="bar" title={`Similarité cosinus : ${value.toFixed(2)}`}>
      <div className={`bar__fill bar__fill--${tone}`} style={{ transform: `scaleX(${stretch(value)})` }} />
      <span className="visually-hidden">{value.toFixed(2)}</span>
    </div>
  );
}
