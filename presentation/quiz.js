/* ================================================================
   Ataraxia — quiz "quel refuge apaiserait ton cœur ?"

   Fonctionnement :
   - 6 questions, chaque réponse ajoute des poids à plusieurs
     lieux-archétypes (weights).
   - À la fin, l'archétype avec le plus haut score est proposé
     avec une description immersive + détails sensoriels + un
     "nudge" qui invite à décrire ce lieu au compagnon Ataraxia.
   - Bouton "copier ma description" met la description dans le
     presse-papier pour la coller ou la relire à voix haute.

   Pas de framework, pas de dépendance : vanilla JS ES6.
   ================================================================ */

// ----------------------------------------------------------------
// 1. Les 8 lieux-archétypes que le quiz peut suggérer
// ----------------------------------------------------------------

const LIEUX = {
  cafe_italien: {
    titre: "Un café en terrasse italienne, en fin d'après-midi doré",
    description: "Une petite terrasse ombragée dans une ruelle pavée, la lumière dorée du soleil descend sur les tables en marbre patiné, le cliquetis des tasses se mêle au parfum du pain chaud et du café fraîchement moulu, un vent tiède fait bruire la glycine qui grimpe au-dessus de toi, tu es assis là, seul mais entouré du bourdonnement doux de la ville.",
    details: {
      "moment": "fin d'après-midi",
      "lumière": "dorée, oblique",
      "sons": "cliquetis de tasses, vent dans les glycines",
      "odeurs": "pain chaud, café, glycine",
      "température": "tiède, vent léger",
      "ambiance": "chaleureuse, contemplative",
    },
    nudge: "Décris ce café au compagnon avec tes mots à toi. Il en fera un lieu où tu pourras vraiment aller.",
  },

  bibliotheque_intime: {
    titre: "La bibliothèque de ton enfance, un soir de pluie",
    description: "Une pièce basse aux étagères de chêne chargées de vieux livres reliés, la lampe à abat-jour vert diffuse une lumière chaude sur le bureau en cuir, la pluie tambourine doucement contre la fenêtre en croisillons, l'odeur du papier ancien et du bois ciré se mêle à celle du thé qui refroidit près de toi, dehors la nuit s'installe sans se presser.",
    details: {
      "moment": "début de soirée",
      "lumière": "chaude, lampe verte",
      "sons": "pluie sur les vitres, craquement du parquet",
      "odeurs": "vieux papier, bois ciré, thé",
      "température": "douce, presque cocon",
      "ambiance": "recueillie, intime",
    },
    nudge: "Cette bibliothèque a peut-être des étagères que tu connais déjà. Raconte-les au compagnon.",
  },

  cabane_foret: {
    titre: "Une cabane en bois au cœur d'une forêt de sapins",
    description: "Une cabane isolée aux poutres apparentes, le feu crépite dans la cheminée en pierre, la lumière tremblante caresse les couvertures épaisses posées sur un fauteuil de cuir, dehors les sapins ploient sous une neige silencieuse, la lueur bleutée du crépuscule filtre à travers les carreaux embués, l'odeur du bois brûlé se mêle à celle du café qui infuse sur le poêle.",
    details: {
      "moment": "crépuscule d'hiver",
      "lumière": "bleutée dehors, orangée dedans",
      "sons": "feu qui crépite, silence de la neige",
      "odeurs": "bois brûlé, café, laine chaude",
      "température": "chaleur du feu, froid dehors",
      "ambiance": "cocon, retrait absolu",
    },
    nudge: "Si le retrait dans les bois te parle, décris cette cabane — les détails précis (une couverture, un livre posé) rendent le monde plus réel.",
  },

  phare_mer: {
    titre: "Un phare isolé sur une côte rocheuse au crépuscule",
    description: "Une pièce circulaire au sommet d'un phare de pierre, les grandes fenêtres donnent sur un océan gris-ardoise qui respire lentement, le halo tournant de la lanterne projette des rayons dorés sur les vagues, l'air salin et frais entre par une lucarne entrouverte, on entend au loin les cormorans, tu tiens un mug fumant entre tes mains, il n'y a personne à des kilomètres.",
    details: {
      "moment": "crépuscule",
      "lumière": "rayons du phare, ciel violacé",
      "sons": "vagues, cormorans, vent",
      "odeurs": "iode, embrun, métal froid",
      "température": "fraîche, vent salin",
      "ambiance": "solitude paisible, souveraine",
    },
    nudge: "Il y a quelque chose de royal dans la solitude d'un phare. Raconte-le au compagnon comme un souvenir qui n'existe pas encore.",
  },

  chalet_montagne: {
    titre: "Un chalet en bois face à un lac de montagne, à l'aube",
    description: "Une véranda en bois clair face à un lac immobile qui reflète les sommets enneigés, l'aube rose se pose sur l'eau et sur la brume qui traîne encore au ras des sapins, un plaid en laine chaude sur les épaules, l'odeur du café et du bois humide se mêle à celle de la mousse, aucun bruit sauf le lointain tintement d'une cloche de vache, une clarté qui semble venir de l'intérieur des choses.",
    details: {
      "moment": "aube",
      "lumière": "rose, brumeuse, cristalline",
      "sons": "silence total, cloche lointaine",
      "odeurs": "bois humide, café, mousse",
      "température": "fraîche, plaid chaud",
      "ambiance": "immensité douce, respiration",
    },
    nudge: "L'aube en montagne a une qualité de silence particulière. Essaie de la nommer avec le compagnon.",
  },

  patio_andalou: {
    titre: "Un patio andalou baigné de midi lent",
    description: "Un patio carré aux murs blanchis à la chaux, une fontaine centrale murmure sous les jasmins et les orangers en pot, la lumière de midi tombe verticale sur les zelliges bleus et blancs du sol, l'ombre découpée d'une arche mauresque étire ses lignes, un vent léger fait tinter des perles suspendues, l'air sent la fleur d'oranger et la pierre chaude, tu es assis dans une fraîcheur inattendue au cœur de la chaleur.",
    details: {
      "moment": "midi",
      "lumière": "verticale, très blanche, contrastée",
      "sons": "fontaine, tintements, cigales lointaines",
      "odeurs": "jasmin, fleur d'oranger, pierre chaude",
      "température": "chaude dehors, fraîche sous l'ombre",
      "ambiance": "élégance ombragée, quiétude",
    },
    nudge: "Ce patio existe dans plein de villes anciennes. Décris celui que ton esprit invente pour toi.",
  },

  temple_japonais: {
    titre: "Un temple bouddhiste dans une forêt de bambous",
    description: "Un petit pavillon de bois sombre aux tuiles courbes posé au bord d'un bassin plein de nénuphars, tu marches pieds nus sur un tatami usé, la lumière filtre en rais verticaux à travers une forêt de bambous denses, une cloche de bronze sonne au loin par intervalles réguliers, l'encens et la mousse humide se répondent, le silence est si construit qu'il en devient une présence, tu t'assois sans plus rien avoir à faire.",
    details: {
      "moment": "matin brumeux",
      "lumière": "filtrée, verte-dorée",
      "sons": "cloche, bambous qui s'entrechoquent, eau",
      "odeurs": "encens, mousse, terre humide",
      "température": "fraîche, humidité douce",
      "ambiance": "recueillement, épure",
    },
    nudge: "L'épure japonaise n'est pas vide — elle est pleine de peu. Décris ce peu au compagnon.",
  },

  grenier_vitraux: {
    titre: "Un grenier avec un vitrail poussiéreux, un jour de pluie",
    description: "Un grenier aux poutres massives et sombres, un vitrail poussiéreux laisse tomber des losanges de couleur sur le plancher usé, la pluie tambourine doucement le toit en ardoise, des malles anciennes s'empilent près d'un fauteuil de velours élimé, l'odeur du bois vieux et des tissus oubliés flotte, tu es là avec un livre ouvert que tu ne lis pas vraiment, le temps s'est arrêté.",
    details: {
      "moment": "après-midi pluvieux",
      "lumière": "tamisée, colorée par le vitrail",
      "sons": "pluie sur les ardoises, craquement du bois",
      "odeurs": "vieux bois, poussière chaude, tissus",
      "température": "douce, un peu poussiéreuse",
      "ambiance": "nostalgique, hors du temps",
    },
    nudge: "Un grenier, c'est un lieu qui garde. Ce que tu voudrais y retrouver, dis-le au compagnon.",
  },
};

// ----------------------------------------------------------------
// 2. Les 6 questions du quiz
//    Chaque réponse a un objet `w` de poids par lieu.
// ----------------------------------------------------------------

const QUESTIONS = [
  {
    q: "Quand tu te sens vraiment bien, il fait plutôt…",
    choices: [
      { label: "frais et humide, un plaid sur les épaules",  w: { cabane_foret: 3, chalet_montagne: 2, grenier_vitraux: 2 } },
      { label: "doux, ni chaud ni froid",                    w: { bibliotheque_intime: 3, temple_japonais: 2, cafe_italien: 1 } },
      { label: "tiède, un vent léger sur la peau",           w: { cafe_italien: 3, patio_andalou: 2, phare_mer: 1 } },
      { label: "chaud, presque cotonneux",                   w: { patio_andalou: 3, cabane_foret: 1, cafe_italien: 1 } },
    ],
  },
  {
    q: "Le son qui t'apaise le plus, c'est…",
    choices: [
      { label: "la pluie fine sur un toit",                  w: { grenier_vitraux: 3, cabane_foret: 2, bibliotheque_intime: 2 } },
      { label: "les vagues, le vent, l'iode",                w: { phare_mer: 4, chalet_montagne: 1 } },
      { label: "le crépitement d'un feu et le silence",      w: { cabane_foret: 3, chalet_montagne: 2, bibliotheque_intime: 1 } },
      { label: "une fontaine, quelques oiseaux",             w: { patio_andalou: 3, temple_japonais: 2, cafe_italien: 1 } },
      { label: "un silence habité, une cloche au loin",      w: { temple_japonais: 3, chalet_montagne: 2, phare_mer: 1 } },
    ],
  },
  {
    q: "Tu préfères être…",
    choices: [
      { label: "seul, au milieu de la nature",               w: { cabane_foret: 3, phare_mer: 3, chalet_montagne: 2, temple_japonais: 2 } },
      { label: "dans un lieu clos, intime, qui te protège",  w: { bibliotheque_intime: 3, grenier_vitraux: 3, cabane_foret: 1 } },
      { label: "entouré discrètement, sentir la vie autour", w: { cafe_italien: 4, patio_andalou: 2 } },
      { label: "entre ciel et terre, en surplomb",           w: { phare_mer: 3, chalet_montagne: 3, temple_japonais: 1 } },
    ],
  },
  {
    q: "La lumière que tu préfères…",
    choices: [
      { label: "l'aube pâle et rose",                        w: { chalet_montagne: 4, temple_japonais: 2 } },
      { label: "midi éclatant mais avec de l'ombre",         w: { patio_andalou: 4, cafe_italien: 1 } },
      { label: "l'après-midi doré",                          w: { cafe_italien: 3, bibliotheque_intime: 1, patio_andalou: 1 } },
      { label: "le crépuscule, violet et long",              w: { phare_mer: 3, cabane_foret: 2, chalet_montagne: 1 } },
      { label: "la nuit tamisée, presque intime",            w: { bibliotheque_intime: 3, grenier_vitraux: 3, cabane_foret: 1 } },
    ],
  },
  {
    q: "Un dimanche pluvieux idéal, c'est…",
    choices: [
      { label: "un café en terrasse couverte, à regarder les gens", w: { cafe_italien: 4 } },
      { label: "un grenier avec un vieux livre",             w: { grenier_vitraux: 4, bibliotheque_intime: 2 } },
      { label: "une balade en forêt sous les gouttes",       w: { cabane_foret: 3, temple_japonais: 2, chalet_montagne: 1 } },
      { label: "un feu de bois et un chat sur les genoux",   w: { cabane_foret: 3, bibliotheque_intime: 2, chalet_montagne: 1 } },
    ],
  },
  {
    q: "La couleur qui t'apaise le plus…",
    choices: [
      { label: "un bleu profond, presque bleu nuit",         w: { phare_mer: 3, temple_japonais: 2, chalet_montagne: 1 } },
      { label: "un vert mousse, végétal, humide",            w: { temple_japonais: 3, cabane_foret: 2, chalet_montagne: 1 } },
      { label: "un ocre chaud, une terre cuite",             w: { patio_andalou: 3, cafe_italien: 2, grenier_vitraux: 1 } },
      { label: "un violet crépuscule, un mauve",             w: { phare_mer: 2, grenier_vitraux: 3, bibliotheque_intime: 1 } },
      { label: "un blanc laiteux, une brume",                w: { temple_japonais: 3, chalet_montagne: 3 } },
    ],
  },
];

// ----------------------------------------------------------------
// 3. État du quiz et rendu
// ----------------------------------------------------------------

const state = {
  step: 0,                 // index de la question courante
  scores: {},              // agrégat de poids par lieu
  answers: [],             // historique des indices choisis (pour "précédent")
};

const el = {
  intro:      document.getElementById("quiz-intro"),
  question:   document.getElementById("quiz-question"),
  result:     document.getElementById("quiz-result"),
  progress:   document.getElementById("quiz-progress"),
  step:       document.getElementById("quiz-step"),
  title:      document.getElementById("quiz-title"),
  choices:    document.getElementById("quiz-choices"),
  back:       document.getElementById("quiz-back"),
  resultTitle:document.getElementById("result-title"),
  resultDesc: document.getElementById("result-desc"),
  resultDet:  document.getElementById("result-details"),
  resultNudge:document.getElementById("result-nudge"),
  startBtn:   document.getElementById("quiz-start"),
  restartBtn: document.getElementById("quiz-restart"),
  copyBtn:    document.getElementById("quiz-copy"),
  copied:     document.getElementById("quiz-copied"),
};

function showPanel(name) {
  el.intro.hidden    = (name !== "intro");
  el.question.hidden = (name !== "question");
  el.result.hidden   = (name !== "result");
}

function renderProgress() {
  el.progress.innerHTML = "";
  for (let i = 0; i < QUESTIONS.length; i++) {
    const d = document.createElement("span");
    d.className = "quiz-dot";
    if (i < state.step) d.classList.add("done");
    else if (i === state.step) d.classList.add("current");
    el.progress.appendChild(d);
  }
}

function renderQuestion() {
  const q = QUESTIONS[state.step];
  el.step.textContent = `question ${state.step + 1} sur ${QUESTIONS.length}`;
  el.title.textContent = q.q;
  el.choices.innerHTML = "";
  q.choices.forEach((c, i) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "quiz-choice";
    btn.type = "button";
    btn.textContent = c.label;
    btn.addEventListener("click", () => pickChoice(i));
    li.appendChild(btn);
    el.choices.appendChild(li);
  });
  el.back.hidden = state.step === 0;
  renderProgress();
}

function pickChoice(choiceIdx) {
  const q = QUESTIONS[state.step];
  const weights = q.choices[choiceIdx].w;
  for (const k of Object.keys(weights)) {
    state.scores[k] = (state.scores[k] || 0) + weights[k];
  }
  state.answers.push(choiceIdx);
  state.step += 1;
  if (state.step >= QUESTIONS.length) {
    renderResult();
  } else {
    renderQuestion();
  }
}

function goBack() {
  if (state.step === 0) return;
  state.step -= 1;
  // On retire les poids de la question courante
  const q = QUESTIONS[state.step];
  const lastChoice = state.answers.pop();
  if (lastChoice != null) {
    const weights = q.choices[lastChoice].w;
    for (const k of Object.keys(weights)) {
      state.scores[k] = (state.scores[k] || 0) - weights[k];
      if (state.scores[k] <= 0) delete state.scores[k];
    }
  }
  renderQuestion();
}

function pickWinner() {
  // Score max ; en cas d'égalité, on prend le plus "haut score absolu"
  // sinon on choisit aléatoirement parmi les ex aequo (mais rare).
  const entries = Object.entries(state.scores);
  if (entries.length === 0) return "cafe_italien"; // fallback improbable
  entries.sort((a, b) => b[1] - a[1]);
  const top = entries[0][1];
  const winners = entries.filter(e => e[1] === top).map(e => e[0]);
  return winners[Math.floor(Math.random() * winners.length)];
}

function renderResult() {
  const key = pickWinner();
  const lieu = LIEUX[key];
  el.resultTitle.textContent = lieu.titre;
  el.resultDesc.textContent = "« " + lieu.description + " »";
  el.resultNudge.textContent = lieu.nudge;

  el.resultDet.innerHTML = "";
  for (const [k, v] of Object.entries(lieu.details)) {
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = v;
    el.resultDet.appendChild(dt);
    el.resultDet.appendChild(dd);
  }

  // Stocke la description courante pour le bouton "copier"
  el.copyBtn.dataset.text = lieu.description;
  el.copied.hidden = true;

  renderProgress();
  showPanel("result");
}

// ----------------------------------------------------------------
// 4. Handlers boutons
// ----------------------------------------------------------------

el.startBtn.addEventListener("click", () => {
  state.step = 0;
  state.scores = {};
  state.answers = [];
  showPanel("question");
  renderQuestion();
});

el.back.addEventListener("click", goBack);

el.restartBtn.addEventListener("click", () => {
  state.step = 0;
  state.scores = {};
  state.answers = [];
  showPanel("intro");
});

el.copyBtn.addEventListener("click", async () => {
  const text = el.copyBtn.dataset.text || "";
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    el.copied.hidden = false;
    setTimeout(() => { el.copied.hidden = true; }, 2500);
  } catch (e) {
    // Fallback : sélectionne le texte pour copie manuelle
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); el.copied.hidden = false; setTimeout(() => { el.copied.hidden = true; }, 2500); }
    catch (_) {}
    document.body.removeChild(ta);
  }
});
