import { useEffect, useState } from "react";
import { MotionConfig } from "motion/react";
import { ApiError, fetchOptions, fetchRecommendations } from "./api";
import type { Answers, Options, RecommendResponse } from "./types";
import { Home } from "./components/Home";
import { Questionnaire, REVIEW_STEP } from "./components/Questionnaire";
import { Results } from "./components/Results";
import { Glass } from "./components/Glass";

const EMPTY_ANSWERS: Answers = {
  description: "",
  liked_wine_reason: "",
  food_or_occasion: "",
  color: "peu importe",
  intensity_likert: null,
  fruity_likert: null,
  woody_likert: null,
  sweetness_likert: null,
  acidity_likert: null,
  oak_tasted: null,
  oak_liked: null,
  aromas: [],
  countries: [],
  max_price: 30,
};

type Screen =
  | { name: "home" }
  | { name: "quiz"; step: number }
  | { name: "analysing" }
  | { name: "results"; response: RecommendResponse }
  | { name: "error"; kind: ApiError["kind"] };

// Durée minimale de l'écran d'analyse : le moteur répond en ~0,3 s, trop vite pour
// que l'on comprenne ce qui se passe. Le verre a le temps de se remplir.
const MIN_ANALYSIS_MS = 1400;

export default function App() {
  const [screen, setScreen] = useState<Screen>({ name: "home" });
  const [answers, setAnswers] = useState<Answers>(EMPTY_ANSWERS);
  const [options, setOptions] = useState<Options | null>(null);
  const [optionsError, setOptionsError] = useState(false);

  const loadOptions = () => {
    setOptionsError(false);
    fetchOptions().then(setOptions, () => setOptionsError(true));
  };
  useEffect(() => {
    loadOptions();
  }, []);

  // Chaque changement d'écran ramène en haut de page.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [screen.name]);

  const submit = async () => {
    setScreen({ name: "analysing" });
    const started = Date.now();
    try {
      const response = await fetchRecommendations(answers);
      const wait = MIN_ANALYSIS_MS - (Date.now() - started);
      if (wait > 0) await new Promise((r) => setTimeout(r, wait));
      setScreen({ name: "results", response });
    } catch (error) {
      setScreen({ name: "error", kind: error instanceof ApiError ? error.kind : "server" });
    }
  };

  const restart = () => {
    setAnswers(EMPTY_ANSWERS);
    setScreen({ name: "home" });
  };

  let content;
  if (optionsError) {
    content = <ErrorScreen kind="offline" onRetry={loadOptions} onEdit={null} />;
  } else if (!options) {
    content = <main className="center" aria-busy="true" />;
  } else if (screen.name === "home") {
    content = <Home wineCount={options.wine_count} onStart={() => setScreen({ name: "quiz", step: 0 })} />;
  } else if (screen.name === "quiz") {
    content = (
      <Questionnaire
        answers={answers}
        options={options}
        initialStep={screen.step}
        onChange={setAnswers}
        onSubmit={submit}
        onExit={() => setScreen({ name: "home" })}
      />
    );
  } else if (screen.name === "analysing") {
    const color = options.colors.find((c) => c.id === answers.color)?.key ?? "any";
    content = (
      <main className="center analysing" aria-live="polite">
        <Glass level={0.7} color={color} className="glass--fill" />
        <p className="analysing__text">Lecture de vos réponses</p>
        <p className="analysing__sub">Comparaison avec {options.wine_count} notes de dégustation</p>
      </main>
    );
  } else if (screen.name === "results") {
    content = (
      <Results
        results={screen.response.results}
        analysis={screen.response.analysis}
        answers={answers}
        options={options}
        onEdit={() => setScreen({ name: "quiz", step: REVIEW_STEP })}
        onRestart={restart}
      />
    );
  } else {
    content = (
      <ErrorScreen
        kind={screen.kind}
        onRetry={submit}
        onEdit={() => setScreen({ name: "quiz", step: REVIEW_STEP })}
      />
    );
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="app">
        <nav className="topbar" aria-label="Navigation principale">
          <button className="topbar__brand" onClick={restart}>
            <img src="/glass.svg" alt="" width={18} height={18} />
            Sommelier sémantique
          </button>
        </nav>
        {content}
        <footer className="disclaimer">
          Prototype éducatif réservé aux adultes, réalisé dans le cadre d'un projet NLP à l'ECE.
          Aucune vente ni incitation à consommer. L'abus d'alcool est dangereux pour la santé, à
          consommer avec modération.
        </footer>
      </div>
    </MotionConfig>
  );
}

const ERRORS: Record<ApiError["kind"], { title: string; text: string }> = {
  offline: {
    title: "Le moteur de recommandation ne répond pas.",
    text: "Lancez l'API depuis la racine du projet avec « uvicorn api.main:app --port 8000 », puis réessayez.",
  },
  no_match: {
    title: "Aucun vin ne correspond à ce budget et à cette couleur.",
    text: "Augmentez le budget ou choisissez « Peu importe » pour la couleur.",
  },
  invalid: {
    title: "Certaines réponses ne sont pas valides.",
    text: "La description doit faire au moins 10 caractères. Vérifiez vos réponses.",
  },
  server: {
    title: "L'analyse a échoué.",
    text: "Le moteur a renvoyé une erreur. Consultez le terminal de l'API, puis réessayez.",
  },
};

function ErrorScreen({
  kind,
  onRetry,
  onEdit,
}: {
  kind: ApiError["kind"];
  onRetry: () => void;
  onEdit: (() => void) | null;
}) {
  const { title, text } = ERRORS[kind];
  const editFirst = kind === "no_match" || kind === "invalid";
  return (
    <main className="center error" role="alert">
      <h1 className="error__title">{title}</h1>
      <p className="error__text">{text}</p>
      <div className="error__actions">
        {onEdit && (
          <button className={`button ${editFirst ? "button--primary" : "button--secondary"}`} onClick={onEdit}>
            Modifier mes réponses
          </button>
        )}
        {!editFirst && (
          <button className="button button--primary" onClick={onRetry}>
            Réessayer
          </button>
        )}
      </div>
    </main>
  );
}
