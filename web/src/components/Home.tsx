import { motion, useReducedMotion } from "motion/react";
import { Glass } from "./Glass";

interface HomeProps {
  wineCount: number;
  onStart: () => void;
}

// Les trois étapes réelles du parcours : ici, la numérotation porte une information.
const STEPS = [
  {
    title: "Vous décrivez",
    text: "Une envie, un souvenir de dégustation, un plat. Avec vos mots, en français ou en anglais.",
  },
  {
    title: "Le modèle lit le sens",
    text: "Vos phrases deviennent des vecteurs sémantiques, comparés aux notes de dégustation de chaque vin et à cinq familles de goûts.",
  },
  {
    title: "Trois vins, expliqués",
    text: "Chaque recommandation montre son score, les phrases qui ont pesé et le profil qu'elle partage avec vous.",
  },
];

export function Home({ wineCount, onStart }: HomeProps) {
  const reduce = useReducedMotion();

  return (
    <main className="home">
      <section className="hero">
        <motion.h1
          className="hero__title"
          initial={reduce ? false : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        >
          Dites-le
          <br />
          avec vos mots.
        </motion.h1>
        <p className="hero__lede">
          Décrivez le vin dont vous avez envie. L'analyse sémantique lit vos phrases et choisit
          trois bouteilles parmi {wineCount} notes de dégustation.
        </p>
        <div className="hero__actions">
          <button className="button button--primary button--large" onClick={onStart} autoFocus>
            Commencer
          </button>
          <p className="hero__age">En continuant, vous confirmez avoir 18 ans ou plus.</p>
        </div>

        {/* Le moment visuel de la page : le verre se remplit une seule fois au chargement. */}
        <motion.div
          className="hero__glass"
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 1 }}
        >
          <Glass level={0.62} color="red" className="glass--pour" />
          <blockquote className="hero__quote">
            « Un rouge souple, avec des fruits rouges, pour un dîner entre amis. »
          </blockquote>
        </motion.div>
      </section>

      <section className="how" aria-labelledby="how-title">
        <h2 id="how-title" className="how__title">
          Pas de filtres à cocher en premier.
          <br />
          Une conversation sur le goût.
        </h2>
        <ol className="how__steps">
          {STEPS.map((step, i) => (
            <li key={step.title} className="how__step">
              <span className="how__index" aria-hidden="true">
                {i + 1}
              </span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
        <button className="button button--light button--large" onClick={onStart}>
          Commencer le questionnaire
        </button>
      </section>
    </main>
  );
}
