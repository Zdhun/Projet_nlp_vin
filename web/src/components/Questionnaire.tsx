import { useEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { Answers, Options, WineColor, YesNo } from "../types";
import { Glass, LIQUID } from "./Glass";

type Update = (patch: Partial<Answers>) => void;

interface StepDef {
  id: string;
  question: string;
  hint?: string;
  /** Faux si la réponse est obligatoire et absente. */
  isValid?: (a: Answers) => boolean;
  optional?: boolean;
  render: (a: Answers, update: Update, options: Options) => ReactNode;
}

const LIKERTS: { key: keyof Answers; label: string; low: string; high: string }[] = [
  { key: "intensity_likert", label: "Intensité", low: "Léger", high: "Puissant" },
  { key: "fruity_likert", label: "Fruité", low: "Discret", high: "Très fruité" },
  { key: "woody_likert", label: "Boisé", low: "Sans bois", high: "Très boisé" },
  { key: "sweetness_likert", label: "Douceur", low: "Sec", high: "Doux" },
  { key: "acidity_likert", label: "Vivacité", low: "Souple", high: "Très vif" },
];

const DESCRIBE_IDEAS = [
  "Un rouge léger et fruité, facile à boire",
  "Un blanc vif et minéral, avec des notes d'agrumes",
  "Un vin rond et boisé, avec de la vanille",
];

const OCCASION_IDEAS = [
  "Un apéritif entre amis",
  "Un barbecue",
  "Des fruits de mer",
  "Un plateau de fromages",
  "Un dîner élégant",
  "Une fête",
];

const MIN_DESCRIPTION = 10;
const PRICE_STEPS = [10, 15, 20, 25, 30, 40, 50, 75, 100, 1000];

function formatBudget(value: number) {
  return value >= 1000 ? "Sans limite" : `${value} $`;
}

/** Ajoute une suggestion à un texte libre sans écraser ce qui est déjà écrit. */
function appendIdea(current: string, idea: string) {
  const text = current.trim();
  if (!text) return idea;
  if (text.toLowerCase().includes(idea.toLowerCase())) return text;
  return `${text.replace(/[.,;]$/, "")}, ${idea.charAt(0).toLowerCase()}${idea.slice(1)}`;
}

function Chip({ selected, onClick, children }: { selected?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="chip" aria-pressed={selected} onClick={onClick}>
      {children}
    </button>
  );
}

function YesNoGroup({ value, onChange, name }: { value: YesNo | null; onChange: (v: YesNo) => void; name: string }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={name}>
      {(["yes", "no"] as const).map((v) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          className="segmented__option"
          onClick={() => onChange(v)}
        >
          {v === "yes" ? "Oui" : "Non"}
        </button>
      ))}
    </div>
  );
}

const STEPS: StepDef[] = [
  {
    id: "describe",
    question: "Décrivez le vin dont vous avez envie.",
    hint: "Arômes, sensations en bouche, humeur du moment. Plus c'est précis, plus le choix l'est.",
    isValid: (a) => a.description.trim().length >= MIN_DESCRIPTION,
    render: (a, update) => (
      <>
        <textarea
          className="field field--large"
          value={a.description}
          onChange={(e) => update({ description: e.target.value })}
          placeholder="Par exemple : un rouge souple aux fruits rouges, pas trop tannique."
          rows={4}
          maxLength={1000}
          aria-label="Description du vin recherché"
          autoFocus
        />
        <div className="chips" aria-label="Idées pour commencer">
          {DESCRIBE_IDEAS.map((idea) => (
            <Chip key={idea} onClick={() => update({ description: idea })}>
              {idea}
            </Chip>
          ))}
        </div>
      </>
    ),
  },
  {
    id: "memory",
    question: "Un vin vous a marqué ? Racontez ce qui vous a plu.",
    hint: "Facultatif. Le souvenir d'une bouteille en dit souvent plus qu'une liste de critères.",
    optional: true,
    render: (a, update) => (
      <textarea
        className="field field--large"
        value={a.liked_wine_reason}
        onChange={(e) => update({ liked_wine_reason: e.target.value })}
        placeholder="Un pinot noir de Bourgogne, très soyeux, avec un parfum de cerise et de sous-bois."
        rows={4}
        maxLength={1000}
        aria-label="Souvenir d'un vin apprécié"
        autoFocus
      />
    ),
  },
  {
    id: "occasion",
    question: "Avec quel plat, ou pour quelle occasion ?",
    hint: "Écrivez librement ou partez d'une suggestion.",
    optional: true,
    render: (a, update) => (
      <>
        <textarea
          className="field"
          value={a.food_or_occasion}
          onChange={(e) => update({ food_or_occasion: e.target.value })}
          placeholder="Un magret de canard, samedi soir."
          rows={2}
          maxLength={500}
          aria-label="Plat ou occasion"
          autoFocus
        />
        <div className="chips">
          {OCCASION_IDEAS.map((idea) => (
            <Chip
              key={idea}
              selected={a.food_or_occasion.toLowerCase().includes(idea.toLowerCase())}
              onClick={() => update({ food_or_occasion: appendIdea(a.food_or_occasion, idea) })}
            >
              {idea}
            </Chip>
          ))}
        </div>
      </>
    ),
  },
  {
    id: "color",
    question: "Plutôt quelle couleur ?",
    render: (a, update, options) => (
      <div className="tiles" role="radiogroup" aria-label="Couleur du vin">
        {options.colors.map((c) => (
          <button
            key={c.id}
            type="button"
            role="radio"
            aria-checked={a.color === c.id}
            className="tile"
            onClick={() => update({ color: c.id })}
          >
            <span
              className={`tile__swatch ${c.key === "any" ? "tile__swatch--any" : ""}`}
              style={{ background: c.key === "any" ? undefined : LIQUID[c.key] }}
              aria-hidden="true"
            />
            {c.label}
          </button>
        ))}
      </div>
    ),
  },
  {
    id: "taste",
    question: "Réglez votre profil de goût.",
    hint: "De 1 à 5. Laissez une ligne vide si vous n'avez pas d'avis.",
    optional: true,
    render: (a, update) => (
      <div className="likerts">
        {LIKERTS.map(({ key, label, low, high }) => {
          const value = a[key] as number | null;
          return (
            <fieldset key={key} className="likert">
              <legend className="likert__label">{label}</legend>
              <div className="likert__scale">
                <span className="likert__end">{low}</span>
                <div className="likert__dots" role="radiogroup" aria-label={label}>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      role="radio"
                      aria-checked={value === n}
                      aria-label={`${label} ${n} sur 5`}
                      className="likert__dot"
                      data-filled={value !== null && n <= value}
                      onClick={() => update({ [key]: value === n ? null : n })}
                    />
                  ))}
                </div>
                <span className="likert__end">{high}</span>
              </div>
            </fieldset>
          );
        })}
      </div>
    ),
  },
  {
    id: "oak",
    question: "Avez-vous déjà goûté un vin élevé en fût de chêne ?",
    hint: "Ces vins ont des notes de vanille, de toasté ou de grillé.",
    optional: true,
    render: (a, update) => (
      <div className="guided">
        <YesNoGroup
          name="Déjà goûté un vin boisé"
          value={a.oak_tasted}
          onChange={(v) => update({ oak_tasted: v, oak_liked: v === "no" ? null : a.oak_liked })}
        />
        <AnimatePresence>
          {a.oak_tasted === "yes" && (
            <motion.div
              className="guided__follow"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <p className="guided__question">Et vous l'avez aimé ?</p>
              <YesNoGroup name="A aimé le vin boisé" value={a.oak_liked} onChange={(v) => update({ oak_liked: v })} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    ),
  },
  {
    id: "aromas",
    question: "Quels arômes aimez-vous retrouver ?",
    hint: "Choisissez-en autant que vous voulez.",
    optional: true,
    render: (a, update, options) => (
      <div className="chips chips--roomy">
        {options.aromas.map((aroma) => {
          const on = a.aromas.includes(aroma.id);
          return (
            <Chip
              key={aroma.id}
              selected={on}
              onClick={() =>
                update({ aromas: on ? a.aromas.filter((x) => x !== aroma.id) : [...a.aromas, aroma.id] })
              }
            >
              {aroma.label}
            </Chip>
          );
        })}
      </div>
    ),
  },
  {
    id: "countries",
    question: "Des pays de prédilection ?",
    hint: "Ils comptent comme une préférence, pas comme un filtre.",
    optional: true,
    render: (a, update, options) => (
      <div className="chips chips--roomy">
        {options.countries.map((country) => {
          const on = a.countries.includes(country.id);
          return (
            <Chip
              key={country.id}
              selected={on}
              onClick={() =>
                update({
                  countries: on ? a.countries.filter((x) => x !== country.id) : [...a.countries, country.id],
                })
              }
            >
              {country.label}
            </Chip>
          );
        })}
      </div>
    ),
  },
  {
    id: "budget",
    question: "Jusqu'à combien par bouteille ?",
    hint: "Prix en dollars US, relevés par Wine Enthusiast au moment de la dégustation.",
    render: (a, update) => {
      const index = Math.max(0, PRICE_STEPS.findIndex((p) => p >= a.max_price));
      return (
        <div className="budget">
          <output className="budget__value" htmlFor="budget">
            {formatBudget(a.max_price)}
          </output>
          <input
            id="budget"
            type="range"
            className="budget__range"
            min={0}
            max={PRICE_STEPS.length - 1}
            step={1}
            value={index}
            aria-valuetext={formatBudget(a.max_price)}
            onChange={(e) => update({ max_price: PRICE_STEPS[Number(e.target.value)] })}
            style={{ ["--fill" as string]: `${(index / (PRICE_STEPS.length - 1)) * 100}%` }}
          />
          <div className="budget__ends" aria-hidden="true">
            <span>10 $</span>
            <span>Sans limite</span>
          </div>
        </div>
      );
    },
  },
];

interface QuestionnaireProps {
  answers: Answers;
  options: Options;
  initialStep: number;
  onChange: (answers: Answers) => void;
  onSubmit: () => void;
  onExit: () => void;
}

export function Questionnaire({ answers, options, initialStep, onChange, onSubmit, onExit }: QuestionnaireProps) {
  const reduce = useReducedMotion();
  const total = STEPS.length + 1; // + écran de relecture
  const [index, setIndex] = useState(initialStep);
  const [direction, setDirection] = useState(1);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const isReview = index === STEPS.length;
  const step = STEPS[index];
  const valid = isReview || !step.isValid || step.isValid(answers);
  const update: Update = (patch) => onChange({ ...answers, ...patch });

  const go = (to: number) => {
    setDirection(to > index ? 1 : -1);
    setIndex(to);
    window.scrollTo({ top: 0 });
  };
  const next = () => {
    if (!valid) return;
    if (isReview) onSubmit();
    else go(index + 1);
  };
  const back = () => (index === 0 ? onExit() : go(index - 1));

  // Le titre de chaque étape reçoit le focus : les lecteurs d'écran annoncent la question.
  useEffect(() => {
    if (!document.activeElement || document.activeElement === document.body) headingRef.current?.focus();
  }, [index]);

  // Entrée valide l'étape ; dans un champ texte, il faut ⌘/Ctrl + Entrée.
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "Enter") return;
    const inTextarea = (e.target as HTMLElement).tagName === "TEXTAREA";
    if (inTextarea && !(e.metaKey || e.ctrlKey)) return;
    if ((e.target as HTMLElement).tagName === "BUTTON") return;
    e.preventDefault();
    next();
  };

  const glassColor: WineColor | "any" =
    options.colors.find((c) => c.id === answers.color)?.key ?? "any";

  return (
    <main className="quiz" onKeyDown={onKeyDown}>
      <aside className="quiz__aside" aria-hidden="true">
        <Glass level={(index + 1) / total} color={glassColor} bubbles={glassColor === "sparkling"} />
      </aside>

      <section className="quiz__main">
        <header className="quiz__top">
          <button type="button" className="link" onClick={back}>
            {index === 0 ? "Accueil" : "Retour"}
          </button>
          <p className="quiz__progress">
            Question {Math.min(index + 1, STEPS.length)} sur {STEPS.length}
          </p>
        </header>
        <div className="progress" aria-hidden="true">
          <div className="progress__bar" style={{ transform: `scaleX(${(index + 1) / total})` }} />
        </div>

        <AnimatePresence mode="wait" custom={direction} initial={false}>
          <motion.div
            key={index}
            className="quiz__step"
            custom={direction}
            initial={reduce ? { opacity: 0 } : { opacity: 0, x: direction * 48 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, x: direction * -48 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            {isReview ? (
              <Review answers={answers} options={options} onEdit={go} headingRef={headingRef} />
            ) : (
              <>
                <h1 className="quiz__question" tabIndex={-1} ref={headingRef}>
                  {step.question}
                </h1>
                {step.hint && <p className="quiz__hint">{step.hint}</p>}
                <div className="quiz__body">{step.render(answers, update, options)}</div>
              </>
            )}
          </motion.div>
        </AnimatePresence>

        <footer className="quiz__nav">
          {step?.id === "describe" && !valid && (
            <p className="quiz__requirement">
              Encore {MIN_DESCRIPTION - answers.description.trim().length} caractères au moins.
            </p>
          )}
          {step?.optional && (
            <button type="button" className="button button--quiet" onClick={() => go(index + 1)}>
              Passer
            </button>
          )}
          <button type="button" className="button button--primary" onClick={next} disabled={!valid}>
            {isReview ? "Trouver mes trois vins" : "Continuer"}
          </button>
        </footer>
      </section>
    </main>
  );
}

/** Dernier écran : relecture des réponses, chaque ligne renvoie à sa question. */
function Review({
  answers,
  options,
  onEdit,
  headingRef,
}: {
  answers: Answers;
  options: Options;
  onEdit: (step: number) => void;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
}) {
  const label = (list: { id: string; label: string }[], ids: string[]) =>
    ids.map((id) => list.find((x) => x.id === id)?.label ?? id).join(", ");
  const likerts = LIKERTS.filter(({ key }) => answers[key] !== null)
    .map(({ key, label: l }) => `${l} ${answers[key]}/5`)
    .join(", ");
  const oak =
    answers.oak_tasted === "no"
      ? "Jamais goûté"
      : answers.oak_liked === "yes"
        ? "Goûté et apprécié"
        : answers.oak_liked === "no"
          ? "Goûté, pas apprécié"
          : "";

  const rows: [string, string, number][] = [
    ["Votre envie", answers.description, 0],
    ["Un vin qui vous a plu", answers.liked_wine_reason, 1],
    ["Plat ou occasion", answers.food_or_occasion, 2],
    ["Couleur", options.colors.find((c) => c.id === answers.color)?.label ?? "", 3],
    ["Profil de goût", likerts, 4],
    ["Vins boisés", oak, 5],
    ["Arômes", label(options.aromas, answers.aromas), 6],
    ["Pays", label(options.countries, answers.countries), 7],
    ["Budget", formatBudget(answers.max_price), 8],
  ];

  return (
    <>
      <h1 className="quiz__question" tabIndex={-1} ref={headingRef}>
        Tout est prêt.
      </h1>
      <p className="quiz__hint">Relisez vos réponses avant de lancer l'analyse.</p>
      <dl className="review">
        {rows.map(([term, value, step]) => (
          <div key={term} className="review__row">
            <dt>{term}</dt>
            <dd className={value ? "" : "review__empty"}>{value || "Sans préférence"}</dd>
            <button type="button" className="link" onClick={() => onEdit(step)} aria-label={`Modifier : ${term}`}>
              Modifier
            </button>
          </div>
        ))}
      </dl>
    </>
  );
}

/** Index de l'écran de relecture (utilisé pour revenir modifier ses réponses). */
export const REVIEW_STEP = STEPS.length;
