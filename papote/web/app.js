/*
  Le comportement de la fenetre.

  Tout ce que la page sait faire passe par `pywebview.api`, c'est-a-dire par
  `passerelle.py`. Ce fichier ne contient aucune regle de francais, aucun
  chemin de fichier, aucune connaissance de Windows : il affiche ce qu'on lui
  donne et renvoie ce qu'on lui demande.

  Deux conventions tenues partout :

  - toute reponse peut contenir « erreur » ou « message ». `repondre()` s'en
    charge une fois pour toutes, plutot que de le refaire a chaque appel ;
  - rien n'est construit avec innerHTML a partir d'une chaine venant de
    Python. Un pseudo contenant « <b> » ne doit pas devenir du gras, et un
    mot inconnu venu d'un texte colle ne doit rien pouvoir injecter.
*/

"use strict";

const $ = (sel) => document.querySelector(sel);

/* Les icones. Dessinees ici en traits de 1,6 pixel, a la meme grille de 24 :
   des icones d'epaisseurs differentes se remarquent tout de suite, meme sans
   savoir pourquoi. Celles de la colonne viennent de `PAGES` ; les autres
   sont posees sur les boutons par l'attribut « data-icone ». */
const ICONES = {
  crayon: "M4 20h4L20 8a2.8 2.8 0 0 0-4-4L4 16v4Z M13.5 6.5l4 4",
  livre: "M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5v-13Z "
       + "M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5v-13Z",
  barres: "M5 20V11 M12 20V4 M19 20v-6",
  fenetre: "M3.5 6.5A2 2 0 0 1 5.5 4.5h13a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-13"
         + "a2 2 0 0 1-2-2v-11Z M3.5 9h17",
  reglages: "M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z "
          + "M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1"
          + "a1.6 1.6 0 0 0-2.7 1.1 2 2 0 1 1-4 0 1.6 1.6 0 0 0-2.7-1.1"
          + "l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3.4 14a2 2 0 1 1 0-4"
          + "a1.6 1.6 0 0 0 1.1-2.7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 10 3.4"
          + "a2 2 0 1 1 4 0 1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1"
          + "A1.6 1.6 0 0 0 20.6 10a2 2 0 1 1 0 4 1.6 1.6 0 0 0-1.2 1Z",
  etincelle: "M12 3.5l1.7 4.8 4.8 1.7-4.8 1.7L12 16.5l-1.7-4.8L5.5 10l4.8-1.7Z"
           + " M18.5 15v4 M16.5 17h4",
  copier: "M9.5 8.5h9a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5h-9"
        + "A1.5 1.5 0 0 1 8 19v-9a1.5 1.5 0 0 1 1.5-1.5Z"
        + " M5.5 15.5A1.5 1.5 0 0 1 4 14V5a1.5 1.5 0 0 1 1.5-1.5h9A1.5 1.5 0 0 1 16 5",
  annuler: "M9 14 4.5 9.5 9 5 M4.5 9.5h10a5 5 0 0 1 0 10H11",
  gomme: "M7.5 20 3.6 16.1a1.6 1.6 0 0 1 0-2.2l9.3-9.3a1.6 1.6 0 0 1 2.2 0l4.3 4.3"
       + "a1.6 1.6 0 0 1 0 2.2L12 20 M7.5 20H20 M8.5 9l6.5 6.5",
  coche: "M5 12.5l4.5 4.5L19 7.5",
  croix: "M7 7l10 10 M17 7 7 17",
  plus: "M12 5.5v13 M5.5 12h13",
  fleche: "M5 12h14 M13.5 6.5 19 12l-5.5 5.5",
  bouclier: "M12 3.5 19 6v5.5c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6Z M9 12l2 2 4-4",
  clavier: "M4.5 6.5h15a1.5 1.5 0 0 1 1.5 1.5v8a1.5 1.5 0 0 1-1.5 1.5h-15"
         + "A1.5 1.5 0 0 1 3 16V8a1.5 1.5 0 0 1 1.5-1.5Z M7 10h.01 M10.5 10h.01"
         + " M14 10h.01 M17 10h.01 M8 14h8",
  curseur: "M7 4.5l11 5.2-4.8 1.6 4 5.1-2.3 1.8-4-5.1-3.3 3.6Z",
  silence: "M9.4 4.6A6 6 0 0 1 18 10c0 2.3.4 4 .9 5.2 M16 18H4.5s2-1.8 2-6.5"
         + " M10.3 20.5a2 2 0 0 0 3.4 0 M4 4l16 16",
  mallette: "M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7"
          + " M4.5 7h15A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15"
          + "A1.5 1.5 0 0 1 3 17.5v-9A1.5 1.5 0 0 1 4.5 7Z M3 12.5h18",
  dossier: "M3.5 7A1.5 1.5 0 0 1 5 5.5h4l2 2h8a1.5 1.5 0 0 1 1.5 1.5v8.5"
         + "A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5Z",
  fichier: "M14 3.5H7.5A1.5 1.5 0 0 0 6 5v14a1.5 1.5 0 0 0 1.5 1.5h9A1.5 1.5 0 0 0 18 19"
         + "V7.5Z M14 3.5v4h4",
  info: "M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17Z M12 11v5 M12 8h.01",
  question: "M12 20.5a8.5 8.5 0 1 0 0-17 8.5 8.5 0 0 0 0 17Z"
          + " M9.6 9.5a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.3-2.4 3.6 M12 16.8h.01",
};

const SVG = "http://www.w3.org/2000/svg";

function icone(nom, taille = 17) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", String(taille));
  svg.setAttribute("height", String(taille));
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.6");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.classList.add("icone");
  const trace = document.createElementNS(SVG, "path");
  trace.setAttribute("d", ICONES[nom] || ICONES.reglages);
  svg.appendChild(trace);
  return svg;
}

/* Les icones des boutons ecrits dans le HTML. Posees une fois, au
   demarrage, avant que quiconque ne recopie le contenu d'un bouton. */
function decorer() {
  document.querySelectorAll("[data-icone]").forEach((element) => {
    if (element.querySelector(":scope > .icone")) return;
    element.insertBefore(icone(element.dataset.icone, 16), element.firstChild);
  });
}

/* -------------------------------------------------------------------------
   Le pont
   ------------------------------------------------------------------------- */

let etat = null;

/* pywebview n'est pret qu'apres son propre evenement ; l'attendre evite le
   premier appel dans le vide, qui laisserait la page blanche. */
function pont() {
  return new Promise((resoudre) => {
    if (window.pywebview && window.pywebview.api) return resoudre(window.pywebview.api);
    window.addEventListener("pywebviewready", () => resoudre(window.pywebview.api),
                            { once: true });
  });
}

async function appeler(methode, ...arguments_) {
  const api = await pont();
  try {
    return await api[methode](...arguments_);
  } catch (e) {
    return { erreur: String(e) };
  }
}

/* Tout ce qui revient de Python passe par ici : le message s'affiche, la
   reponse continue son chemin. */
function repondre(reponse) {
  if (!reponse) return {};
  if (reponse.erreur) dire(reponse.erreur, "alerte");
  else if (reponse.message) dire(reponse.message, "succes");
  if (reponse.reglages && etat) etat.reglages = reponse.reglages;
  return reponse;
}

let minuterieToast = null;
function dire(message, ton) {
  const toast = $("#toast");
  toast.textContent = insecables(message);
  toast.className = "toast visible" + (ton ? " " + ton : "");
  clearTimeout(minuterieToast);
  minuterieToast = setTimeout(() => toast.classList.remove("visible"), 4200);
}

/* Un bouton qui efface demande a etre presse deux fois.

   Deux boutons de cette fenetre detruisent quelque chose qu'on ne peut pas
   reconstituer : l'historique des fautes et le journal. Un clic de trop et
   tout est parti, sans avertissement et sans retour. Le premier clic arme,
   le second agit, et l'arme retombe toute seule si l'on s'en va.

   Le contenu du bouton est mis de cote plutot que son seul texte : une
   icone perdue au premier clic ne revenait jamais. */
const DELAI_CONFIRMATION = 4000;

function armer(selecteur, action) {
  const bouton = $(selecteur);
  const contenu = Array.from(bouton.childNodes);
  let arme = false;
  let minuterie = null;

  function desarmer() {
    clearTimeout(minuterie);
    if (!arme) return;
    arme = false;
    bouton.replaceChildren(...contenu);
    bouton.classList.remove("arme");
  }

  bouton.addEventListener("click", async () => {
    if (!arme) {
      arme = true;
      bouton.textContent = "Confirmer ?";
      bouton.classList.add("arme");
      minuterie = setTimeout(desarmer, DELAI_CONFIRMATION);
      return;
    }
    desarmer();
    await action();
  });
  bouton.addEventListener("blur", desarmer);
}


/* -------------------------------------------------------------------------
   Petits assembleurs
   ------------------------------------------------------------------------- */

function creer(balise, classe, texte) {
  const element = document.createElement(balise);
  if (classe) element.className = classe;
  if (texte !== undefined) element.textContent = texte;
  return element;
}

function vider(element) {
  while (element.firstChild) element.removeChild(element.firstChild);
  return element;
}

/* Un bouton avec une icone devant son libelle. */
function boutonIcone(classe, nomIcone, libelle) {
  const bouton = creer("button", classe);
  bouton.type = "button";
  bouton.appendChild(icone(nomIcone, 15));
  if (libelle) bouton.appendChild(document.createTextNode(libelle));
  return bouton;
}

/* Le petit « retirer » des listes : une croix, nommee pour qui ne la voit
   pas. */
function boutonRetirer(quoi, surRetrait) {
  const bouton = boutonIcone("retirer", "croix");
  bouton.title = "Retirer";
  bouton.setAttribute("aria-label", "Retirer " + quoi);
  bouton.addEventListener("click", surRetrait);
  return bouton;
}

function bascule(actif, surChangement) {
  const bouton = creer("button", "bascule");
  bouton.type = "button";
  bouton.setAttribute("role", "switch");
  bouton.setAttribute("aria-checked", String(!!actif));
  bouton.addEventListener("click", () => {
    const nouveau = bouton.getAttribute("aria-checked") !== "true";
    bouton.setAttribute("aria-checked", String(nouveau));
    surChangement(nouveau);
  });
  return bouton;
}

/* Un contrôle segmenté : plusieurs choix, un seul retenu. Il sert au ton
   comme à la position de la bulle ; les écrire deux fois, c'était les voir
   diverger. `apres` est appelé au départ puis à chaque choix : certains
   réglages changent ce que la page affiche autour d'eux. */
function segments(zone, choix, reglage, apres) {
  vider(zone);
  zone.setAttribute("role", "group");
  choix.forEach((option) => {
    const bouton = creer("button", "segment");
    bouton.type = "button";
    bouton.dataset.cle = option.cle;
    bouton.appendChild(creer("span", "segment-nom", option.nom));
    if (option.explication) bouton.title = option.explication;
    else bouton.title = option.nom;
    bouton.setAttribute("aria-pressed",
                        String(etat.reglages[reglage] === option.cle));
    bouton.addEventListener("click", async () => {
      etat.reglages[reglage] = option.cle;
      zone.querySelectorAll(".segment").forEach((autre) => {
        autre.setAttribute("aria-pressed", String(autre === bouton));
      });
      if (apres) apres(option.cle);
      repondre(await appeler("regler", reglage, option.cle));
    });
    zone.appendChild(bouton);
  });
  if (apres) apres(etat.reglages[reglage]);
}


/* Une rangee de reglage : ce que c'est, a gauche ; de quoi le changer, a
   droite. Pour un interrupteur, toute la rangee se clique : viser un
   bouton de quarante pixels quand le libelle en fait trois cents, c'est
   rater une fois sur deux. */
function ligne(titre, explication, controle) {
  const rangee = creer("div", "ligne-action");
  const textes = creer("div");
  textes.appendChild(creer("div", "ligne-titre", titre));
  if (explication) textes.appendChild(creer("div", "aide", explication));
  rangee.appendChild(textes);
  rangee.appendChild(controle);
  if (controle.getAttribute("role") === "switch") {
    controle.setAttribute("aria-label", titre);
    rangee.classList.add("cliquable");
    rangee.addEventListener("click", (evenement) => {
      if (!controle.contains(evenement.target)) controle.click();
    });
  }
  return rangee;
}

function jeton(texte, surRetrait) {
  const element = creer("li", "jeton");
  element.appendChild(creer("span", "jeton-texte", texte));
  element.appendChild(boutonRetirer(texte, surRetrait));
  return element;
}

function sinon(liste, message) {
  if (!liste.childElementCount) liste.appendChild(creer("li", "vide", message));
}

/* Le nombre d'elements d'une liste, a cote de son titre. */
function compterDans(selecteur, nombre) {
  const pastille = $(selecteur);
  pastille.textContent = nombre ? String(nombre) : "";
  pastille.hidden = !nombre;
}

const NOMBRE = new Intl.NumberFormat("fr-FR");

/* Les espaces de la typographie francaise, avant « : ; ? ! » et a
   l'interieur des guillemets, deviennent insecables a l'affichage : sans
   cela, un « » orphelin tombait seul en debut de ligne. Le texte de
   l'utilisateur n'est jamais touche, seulement nos explications. */
function insecables(texte) {
  return String(texte || "")
    .replace(/ ([:;?!»])/g, "\u00a0$1")
    .replace(/« /g, "«\u00a0");
}

/* -------------------------------------------------------------------------
   Navigation
   ------------------------------------------------------------------------- */

const RAFRAICHIR = {
  dictionnaire: chargerDictionnaire,
  fautes: chargerFautes,
  applications: chargerApplications,
  reglages: () => { chargerJournal(); chargerConfidentialite(); },
};

function pageActive() {
  const section = document.querySelector(".page.active");
  return section ? section.dataset.page : null;
}

function afficher(cle) {
  const page = etat.pages.find((p) => p.cle === cle) || etat.pages[0];
  fermerInfobulle();
  document.querySelectorAll(".page").forEach((section) => {
    section.classList.toggle("active", section.dataset.page === page.cle);
  });
  document.querySelectorAll(".entree").forEach((entree) => {
    if (entree.dataset.page === page.cle) entree.setAttribute("aria-current", "page");
    else entree.removeAttribute("aria-current");
  });
  $("#titre-page").textContent = page.nom;
  $("#soustitre-page").textContent = page.soustitre;
  $("#defile").scrollTop = 0;
  $("#principal").classList.remove("defilee");
  if (RAFRAICHIR[page.cle]) RAFRAICHIR[page.cle]();
}

/* -------------------------------------------------------------------------
   Page « Corriger »

   Le champ est la seule source du texte. Apres une correction, il cede sa
   place a un rendu en lecture seule — meme police, meme marge, meme
   hauteur — ou chaque mot change est souligne : on voit d'un coup d'oeil ce
   qui a bouge, et un clic sur le mot dit pourquoi. Un clic ailleurs dans le
   texte rend la plume, le curseur la ou l'on a clique.
   ------------------------------------------------------------------------- */

/* La derniere relecture : les corrections, chacune refusable, et les mots
   dont le correcteur n'est pas sur. Null tant que rien n'a ete corrige. */
let relecture = null;

/* Le texte tel que le programme l'a ecrit pour la derniere fois. S'il
   differe du champ, c'est que l'utilisateur a repris la main : les
   soulignements ne correspondraient plus a rien. */
let dernierTexteEcrit = "";

function ecrire(texte) {
  $("#champ").value = texte;
  dernierTexteEcrit = texte;
  compter();
}

function compter() {
  const valeur = $("#champ").value;
  const texte = valeur.trim();
  const mots = texte ? texte.split(/\s+/).length : 0;
  const compteur = vider($("#compteur"));
  if (mots) {
    compteur.appendChild(document.createTextNode(
      NOMBRE.format(mots) + (mots > 1 ? " mots" : " mot")));
    compteur.appendChild(creer("span", "signes", " · " + NOMBRE.format(valeur.length)
      + (valeur.length > 1 ? " signes" : " signe")));
  }
  $("#relecture").classList.toggle("perimee", !!relecture && relecturePerimee());
}

function relecturePerimee() {
  return $("#champ").value !== dernierTexteEcrit;
}

/* Ce que le texte etait avant que le programme n'y touche.

   « Corriger » reecrit le champ par-dessus l'original, et Ctrl+Z ne defait
   pas ce qu'un programme a ecrit : le texte d'avant n'existait plus nulle
   part. Quelqu'un qui colle un texte, corrige, et n'aime pas le resultat
   n'avait aucun moyen de revenir.

   La relecture est retenue avec le texte : annuler un refus fait revenir
   le soulignement qu'il avait efface. */
const etatsPrecedents = [];
const PROFONDEUR_ANNULATION = 20;

function retenirLetat() {
  etatsPrecedents.push({
    texte: $("#champ").value,
    relecture: relecture ? JSON.parse(JSON.stringify(relecture)) : null,
    mode: modeActuel(),
  });
  if (etatsPrecedents.length > PROFONDEUR_ANNULATION) etatsPrecedents.shift();
  majAnnuler();
}

function majAnnuler() {
  $("#annuler").hidden = etatsPrecedents.length === 0;
}

function annulerLaDerniere() {
  if (!etatsPrecedents.length) return;
  const precedent = etatsPrecedents.pop();
  $("#annuler").hidden = etatsPrecedents.length === 0;
  ecrire(precedent.texte);
  relecture = precedent.relecture;
  montrerRelecture();
  if (precedent.mode === "relecture" && relecture) passerEnRelecture();
  else passerEnEdition();
  dire("Texte rétabli.", "succes");
}

let correctionEnCours = false;

function etiqueterCorriger(enCours) {
  const bouton = vider($("#corriger"));
  bouton.disabled = enCours;
  bouton.setAttribute("aria-busy", String(enCours));
  if (enCours) {
    bouton.appendChild(creer("span", "rouet"));
    bouton.appendChild(document.createTextNode("Correction…"));
  } else {
    bouton.appendChild(icone("etincelle", 16));
    bouton.appendChild(document.createTextNode("Corriger"));
    bouton.appendChild(creer("kbd", null, "Ctrl ↵"));
  }
}

async function corriger() {
  const champ = $("#champ");
  if (!champ.value.trim() || correctionEnCours) return;
  fermerInfobulle();
  const avant = champ.value;
  retenirLetat();

  correctionEnCours = true;
  etiqueterCorriger(true);
  const reponse = repondre(await appeler("corriger", avant));
  correctionEnCours = false;
  etiqueterCorriger(false);

  // Rien n'a change : l'annulation n'aurait rien a rendre.
  if (reponse.erreur || reponse.texte === avant) {
    etatsPrecedents.pop();
    majAnnuler();
  }
  if (reponse.erreur) return;

  ecrire(reponse.texte);
  montrerResultat(reponse);

  const corrections = reponse.corrections || [];
  const inconnus = reponse.inconnus || [];
  if (!corrections.length && !inconnus.length) {
    dire("Aucune faute trouvée.", "succes");
  } else if (corrections.length) {
    const n = corrections.length;
    dire(n + (n > 1 ? " corrections appliquées." : " correction appliquée."),
         "succes");
  }
}

/* Ce que rend « corriger », mis en forme pour la page. */
function montrerResultat(reponse) {
  relecture = {
    corrections: (reponse.corrections || []).map((c) => ({
      avant: c.avant, apres: c.apres, message: c.message || "",
      refusee: false,
    })),
    inconnus: (reponse.inconnus || []).map((i) => ({
      mot: i.mot, propositions: i.propositions || [],
    })),
  };
  montrerRelecture();
  if (relecture.corrections.length || relecture.inconnus.length) {
    passerEnRelecture();
  } else {
    passerEnEdition(undefined, document.activeElement === $("#champ"));
  }
}

function montrerRelecture() {
  const r = relecture;
  $("#accueil").hidden = !!r;
  $("#relecture").hidden = !r;
  montrerCorrections(r ? r.corrections : []);
  montrerInconnus(r ? r.inconnus : []);
  if (!r) return;

  const actives = r.corrections.filter((c) => !c.refusee).length;
  const pastilleC = $("#pastille-corrections");
  pastilleC.hidden = !actives;
  pastilleC.textContent = actives + (actives > 1 ? " corrections" : " correction");
  const pastilleI = $("#pastille-inconnus");
  pastilleI.hidden = !r.inconnus.length;
  pastilleI.textContent = r.inconnus.length + " à vérifier";

  $("#propre").hidden = r.corrections.length > 0 || r.inconnus.length > 0;
  $("#relecture").classList.toggle("perimee", relecturePerimee());
  if (modeActuel() === "relecture") dessinerRendu();
}

/* Chaque correction dit pourquoi elle a ete faite, et peut etre refusee
   seule. Une puce barree ne suffisait pas : on voyait ce qui avait change,
   jamais la raison — et pour revenir sur une seule correction, il fallait
   tout annuler. */
function montrerCorrections(corrections) {
  const zone = vider($("#corrections"));
  zone.hidden = !corrections.length;
  if (!corrections.length) return;

  zone.appendChild(teteDeGroupe("Corrigé dans le texte",
    "Gardez votre version d'un clic, ici seulement."));
  const liste = creer("ul", "groupe-lignes");
  corrections.forEach((correction, rang) => {
    const rangee = creer("li", "correction" + (correction.refusee ? " refusee" : ""));
    rangee.dataset.rang = String(rang);
    rangee.style.animationDelay = Math.min(rang * 28, 320) + "ms";

    const puce = creer("span", "puce");
    puce.appendChild(icone(correction.refusee ? "annuler" : "coche", 14));
    rangee.appendChild(puce);

    const corps = creer("div", "corps");
    corps.appendChild(changement(correction));
    corps.appendChild(creer("div", "pourquoi", insecables(correction.message)));
    rangee.appendChild(corps);

    if (correction.refusee) {
      rangee.appendChild(creer("span", "etiquette", "Gardé tel quel"));
    } else {
      const garder = boutonIcone("bouton discret minuscule", "annuler",
                                 "Garder « " + correction.avant + " »");
      garder.title = "Remettre ce que vous aviez écrit, ici seulement";
      garder.addEventListener("click", () => refuser(rang));
      rangee.appendChild(garder);
      relier(rangee, "corrige", rang);
    }
    liste.appendChild(rangee);
  });
  zone.appendChild(liste);
}

function teteDeGroupe(titre, aide) {
  const tete = creer("div", "groupe-liste-tete");
  tete.appendChild(creer("h3", null, titre));
  if (aide) tete.appendChild(creer("span", "aide", aide));
  return tete;
}

function changement(correction) {
  const element = creer("span", "changement");
  element.appendChild(creer("del", null, correction.avant));
  const fleche = creer("span", "fleche");
  fleche.appendChild(icone("fleche", 13));
  element.appendChild(fleche);
  element.appendChild(creer("ins", null, correction.apres));
  return element;
}

/* Survoler une ligne de la liste eclaire son mot dans le texte, et la
   cliquer ouvre l'explication a cote du mot : la liste sert d'index. */
function relier(rangee, type, rang) {
  const repere = () => document.querySelector(
    `#rendu .repere[data-type="${type}"][data-rang="${rang}"]`);
  rangee.addEventListener("mouseenter", () => {
    const r = repere();
    if (r) r.classList.add("eclaire");
  });
  rangee.addEventListener("mouseleave", () => {
    const r = repere();
    if (r) r.classList.remove("eclaire");
  });
  rangee.addEventListener("click", (evenement) => {
    if (evenement.target.closest("button")) return;
    if (modeActuel() !== "relecture" && !relecturePerimee()) passerEnRelecture();
    const r = repere();
    if (!r) return;
    r.scrollIntoView({ block: "nearest" });
    ouvrirInfobulle(r);
  });
}

async function refuser(rang) {
  const correction = relecture && relecture.corrections[rang];
  if (!correction || correction.refusee) return;
  retenirLetat();
  const reponse = repondre(await appeler(
    "retablir", $("#champ").value, correction.avant, correction.apres));
  if (reponse.erreur || !reponse.retablie) {
    etatsPrecedents.pop();
    majAnnuler();
    if (!reponse.erreur) {
      dire("« " + correction.apres + " » n'est plus dans le texte.", "alerte");
    }
    return;
  }
  const perimee = relecturePerimee();
  $("#champ").value = reponse.texte;
  if (!perimee) dernierTexteEcrit = reponse.texte;
  compter();
  correction.refusee = true;
  apresUnGeste();
  dire("« " + correction.avant + " » rétabli.", "succes");
}

/* Apres un refus, un remplacement ou un ajout : la bulle se ferme, la
   relecture se redessine, et le clavier retrouve le texte plutot que de
   tomber dans le vide avec le mot qui vient de disparaitre. */
function apresUnGeste() {
  const auClavier = $("#infobulle").contains(document.activeElement);
  fermerInfobulle();
  montrerRelecture();
  if (auClavier && modeActuel() === "relecture") $("#rendu").focus({ preventScroll: true });
}

/* Les mots dont le correcteur n'est pas sur. Il se tait plutot que d'inventer
   une faute ; c'est ici qu'ils reviennent, avec de quoi choisir. */
function montrerInconnus(inconnus) {
  const zone = vider($("#inconnus"));
  zone.hidden = !inconnus.length;
  if (!inconnus.length) return;

  zone.appendChild(teteDeGroupe("À vérifier",
    "Papote ne connaît pas ces mots, et préfère demander."));
  const liste = creer("ul", "groupe-lignes");
  inconnus.forEach((inconnu, rang) => {
    const rangee = creer("li", "inconnu");
    rangee.style.animationDelay = Math.min(rang * 40, 320) + "ms";

    const puce = creer("span", "puce");
    puce.appendChild(icone("question", 14));
    rangee.appendChild(puce);

    const corps = creer("div", "corps");
    corps.appendChild(creer("span", "inconnu-mot", inconnu.mot));
    corps.appendChild(propositions(inconnu));
    rangee.appendChild(corps);

    rangee.appendChild(boutonGarderLeMot(inconnu, "bouton discret minuscule"));
    relier(rangee, "douteux", rang);
    liste.appendChild(rangee);
  });
  zone.appendChild(liste);
}

function propositions(inconnu) {
  const zone = creer("div", "propositions");
  if (!inconnu.propositions.length) {
    zone.appendChild(creer("span", "aide", "Aucune proposition."));
    return zone;
  }
  inconnu.propositions.forEach((proposition) => {
    const bouton = creer("button", "proposition", proposition);
    bouton.type = "button";
    bouton.title = "Remplacer « " + inconnu.mot + " » par « " + proposition + " »";
    bouton.addEventListener("click", () => remplacerInconnu(inconnu, proposition));
    zone.appendChild(bouton);
  });
  return zone;
}

function boutonGarderLeMot(inconnu, classe) {
  const bouton = boutonIcone(classe, "plus", "Ajouter au dictionnaire");
  bouton.title = "« " + inconnu.mot + " » ne sera plus signalé";
  bouton.addEventListener("click", () => garderLeMot(inconnu));
  return bouton;
}

async function remplacerInconnu(inconnu, proposition) {
  retenirLetat();
  const reponse = repondre(
    await appeler("remplacer", $("#champ").value, inconnu.mot, proposition));
  if (reponse.erreur) {
    etatsPrecedents.pop();
    majAnnuler();
    return;
  }
  const perimee = relecturePerimee();
  $("#champ").value = reponse.texte;
  if (!perimee) dernierTexteEcrit = reponse.texte;
  compter();
  relecture.inconnus = (reponse.inconnus || []).map((i) => ({
    mot: i.mot, propositions: i.propositions || [],
  }));
  apresUnGeste();
  dire("« " + inconnu.mot + " » remplacé par « " + proposition + " ».", "succes");
}

async function garderLeMot(inconnu) {
  const reponse = repondre(await appeler("ajouter_mot", inconnu.mot));
  if (reponse.erreur || !relecture) return;
  const cle = inconnu.mot.toLowerCase();
  relecture.inconnus = relecture.inconnus.filter((i) => i.mot.toLowerCase() !== cle);
  apresUnGeste();
}

/* -- les deux vues du texte ------------------------------------------------ */

function modeActuel() {
  return $("#editeur").dataset.mode;
}

function passerEnRelecture() {
  const champ = $("#champ");
  const rendu = $("#rendu");
  const avaitLeFocus = document.activeElement === champ;
  const defilement = champ.scrollTop;
  dessinerRendu();
  $("#editeur").dataset.mode = "relecture";
  rendu.hidden = false;
  champ.hidden = true;
  rendu.scrollTop = defilement;
  $("#modifier").hidden = false;
  if (avaitLeFocus) rendu.focus({ preventScroll: true });
}

function passerEnEdition(position, prendreLeFocus = true) {
  const champ = $("#champ");
  const rendu = $("#rendu");
  const etaitEnRelecture = modeActuel() === "relecture";
  const defilement = rendu.scrollTop;
  fermerInfobulle();
  $("#editeur").dataset.mode = "edition";
  champ.hidden = false;
  rendu.hidden = true;
  $("#modifier").hidden = true;
  if (etaitEnRelecture) champ.scrollTop = defilement;
  if (!prendreLeFocus) return;
  champ.focus({ preventScroll: true });
  if (typeof position === "number") champ.setSelectionRange(position, position);
}

/* Les mots se cherchent entiers, comme Python les cherche dans
   `retablir` et `remplacer` : souligner un mot que le refus ne trouverait
   pas, ce serait promettre un bouton qui ne fait rien. */
function motif(mot) {
  const echappe = mot.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp("(?<![\\p{L}\\p{N}_])" + echappe + "(?![\\p{L}\\p{N}_])", "gu");
}

function trouver(texte, mot, prises, toutes) {
  const trouvees = [];
  for (const occurrence of texte.matchAll(motif(mot))) {
    const debut = occurrence.index;
    const fin = debut + occurrence[0].length;
    if (prises.some((p) => debut < p.fin && fin > p.debut)) continue;
    trouvees.push({ debut, fin });
    if (!toutes) break;
  }
  return trouvees;
}

function dessinerRendu() {
  const texte = $("#champ").value;
  const rendu = vider($("#rendu"));
  const plages = [];
  if (relecture) {
    relecture.corrections.forEach((correction, rang) => {
      if (correction.refusee || !(correction.apres || "").trim()) return;
      const [plage] = trouver(texte, correction.apres, plages, false);
      if (plage) plages.push({ ...plage, type: "corrige", rang });
    });
    relecture.inconnus.forEach((inconnu, rang) => {
      trouver(texte, inconnu.mot, plages, true).forEach((plage) => {
        plages.push({ ...plage, type: "douteux", rang });
      });
    });
  }
  plages.sort((a, b) => a.debut - b.debut);

  let curseur = 0;
  plages.forEach((plage) => {
    if (plage.debut > curseur) {
      rendu.appendChild(document.createTextNode(texte.slice(curseur, plage.debut)));
    }
    const repere = creer("mark", "repere " + plage.type,
                         texte.slice(plage.debut, plage.fin));
    repere.dataset.type = plage.type;
    repere.dataset.rang = String(plage.rang);
    repere.tabIndex = 0;
    repere.setAttribute("role", "button");
    repere.setAttribute("aria-haspopup", "dialog");
    repere.setAttribute("aria-expanded", "false");
    if (plage.type === "corrige") {
      const c = relecture.corrections[plage.rang];
      repere.setAttribute("aria-label",
        c.apres + " : corrigé, vous aviez écrit « " + c.avant + " »");
    } else {
      repere.setAttribute("aria-label",
        relecture.inconnus[plage.rang].mot + " : mot à vérifier");
    }
    rendu.appendChild(repere);
    curseur = plage.fin;
  });
  if (curseur < texte.length) rendu.appendChild(document.createTextNode(texte.slice(curseur)));
  // Un retour a la ligne final ne se dessine pas dans un bloc : le champ,
  // lui, le montre. Sans ce double, la derniere ligne sauterait.
  if (texte.endsWith("\n")) rendu.appendChild(document.createTextNode("\n"));
}

/* Ou tombe un clic, compte en caracteres depuis le debut du texte. Le
   rendu contient exactement le texte du champ, mot pour mot : la longueur
   de ce qui precede le point clique est donc la position dans le champ. */
function positionDuClic(evenement) {
  const rendu = $("#rendu");
  const longueur = $("#champ").value.length;
  const point = document.caretRangeFromPoint
    ? document.caretRangeFromPoint(evenement.clientX, evenement.clientY) : null;
  if (!point || !rendu.contains(point.startContainer)) return longueur;
  const avant = document.createRange();
  avant.setStart(rendu, 0);
  avant.setEnd(point.startContainer, point.startOffset);
  return Math.min(avant.toString().length, longueur);
}

/* -- l'infobulle d'un mot souligne ------------------------------------------ */

let repereOuvert = null;

function ouvrirInfobulle(repere, auClavier = false) {
  if (repereOuvert === repere) { fermerInfobulle(); return; }
  fermerInfobulle();
  const bulle = vider($("#infobulle"));
  const rang = Number(repere.dataset.rang);
  bulle.className = "infobulle " + repere.dataset.type;

  if (repere.dataset.type === "corrige") {
    const correction = relecture.corrections[rang];
    bulle.setAttribute("aria-label", "Correction de « " + correction.avant + " »");
    bulle.appendChild(creer("div", "infobulle-genre", "Corrigé"));
    bulle.appendChild(changement(correction));
    if (correction.message) {
      bulle.appendChild(creer("p", "infobulle-texte", insecables(correction.message)));
    }
    const actions = creer("div", "infobulle-actions");
    const garder = boutonIcone("bouton minuscule", "annuler",
                               "Garder « " + correction.avant + " »");
    garder.addEventListener("click", () => refuser(rang));
    actions.appendChild(garder);
    bulle.appendChild(actions);
  } else {
    const inconnu = relecture.inconnus[rang];
    bulle.setAttribute("aria-label", "Mot à vérifier : " + inconnu.mot);
    bulle.appendChild(creer("div", "infobulle-genre", "À vérifier"));
    bulle.appendChild(creer("p", "infobulle-texte", insecables(
      inconnu.propositions.length
        ? "Papote ne connaît pas « " + inconnu.mot + " ». Vouliez-vous dire :"
        : "Papote ne connaît pas « " + inconnu.mot + " ».")));
    if (inconnu.propositions.length) bulle.appendChild(propositions(inconnu));
    const actions = creer("div", "infobulle-actions");
    actions.appendChild(boutonGarderLeMot(inconnu, "bouton discret minuscule"));
    bulle.appendChild(actions);
  }

  bulle.hidden = false;
  placerInfobulle(bulle, repere);
  repere.setAttribute("aria-expanded", "true");
  repere.classList.add("ouvert");
  repereOuvert = repere;
  if (auClavier) {
    const premier = bulle.querySelector("button");
    if (premier) premier.focus();
  }
}

function placerInfobulle(bulle, repere) {
  const cadre = repere.getBoundingClientRect();
  const largeur = bulle.offsetWidth;
  const hauteur = bulle.offsetHeight;
  const marge = 12;
  let x = cadre.left + cadre.width / 2 - largeur / 2;
  x = Math.max(marge, Math.min(x, window.innerWidth - largeur - marge));
  let y = cadre.bottom + 8;
  let dessous = true;
  if (y + hauteur > window.innerHeight - marge && cadre.top - hauteur - 8 > marge) {
    y = cadre.top - hauteur - 8;
    dessous = false;
  }
  bulle.style.left = Math.round(x) + "px";
  bulle.style.top = Math.round(y) + "px";
  bulle.dataset.cote = dessous ? "dessous" : "dessus";
}

/* La bulle suit son mot quand le texte defile, et se ferme quand le mot
   sort de la vue : une bulle qui pointe dans le vide ne dit plus rien. */
function suivreLeRepere() {
  if (!repereOuvert) return;
  const mot = repereOuvert.getBoundingClientRect();
  const vue = $("#rendu").getBoundingClientRect();
  const page = $("#defile").getBoundingClientRect();
  const haut = Math.max(vue.top, page.top);
  const bas = Math.min(vue.bottom, page.bottom);
  if (mot.bottom < haut || mot.top > bas) { fermerInfobulle(); return; }
  placerInfobulle($("#infobulle"), repereOuvert);
}

function fermerInfobulle(rendreLeFocus = false) {
  const bulle = $("#infobulle");
  if (!bulle || bulle.hidden) return;
  bulle.hidden = true;
  const repere = repereOuvert;
  repereOuvert = null;
  if (!repere) return;
  repere.setAttribute("aria-expanded", "false");
  repere.classList.remove("ouvert");
  if (rendreLeFocus && repere.isConnected) repere.focus({ preventScroll: true });
  else if (rendreLeFocus && modeActuel() === "relecture") {
    $("#rendu").focus({ preventScroll: true });
  }
}

function brancherLeTexte() {
  const champ = $("#champ");
  const rendu = $("#rendu");

  champ.addEventListener("input", compter);

  // Cliquer pour placer le curseur, puis repartir sans rien changer : les
  // soulignements reviennent. Ils ne valent plus rien des que le texte a
  // bouge, et restent alors effaces.
  champ.addEventListener("blur", () => {
    if (!relecture || relecturePerimee() || !document.hasFocus()) return;
    if (!relecture.corrections.some((c) => !c.refusee) && !relecture.inconnus.length) return;
    setTimeout(() => {
      if (document.activeElement !== champ && modeActuel() === "edition"
          && !relecturePerimee()) {
        passerEnRelecture();
      }
    }, 0);
  });

  rendu.addEventListener("click", (evenement) => {
    const repere = evenement.target.closest(".repere");
    if (repere) { ouvrirInfobulle(repere); return; }
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed && rendu.contains(selection.anchorNode)) return;
    passerEnEdition(positionDuClic(evenement));
  });

  rendu.addEventListener("keydown", (evenement) => {
    const repere = evenement.target.closest && evenement.target.closest(".repere");
    if (repere && (evenement.key === "Enter" || evenement.key === " ")) {
      evenement.preventDefault();
      ouvrirInfobulle(repere, true);
      return;
    }
    if (evenement.ctrlKey || evenement.metaKey || evenement.altKey) return;
    // Taper dans le rendu, c'est vouloir ecrire : le champ reprend la
    // main, curseur a la fin, et la touche y tombe.
    if (evenement.key.length === 1 || evenement.key === "Backspace"
        || evenement.key === "Enter") {
      passerEnEdition($("#champ").value.length);
    }
  });

  $("#modifier").addEventListener("click", () => passerEnEdition(champ.value.length));

  document.addEventListener("mousedown", (evenement) => {
    if (!repereOuvert) return;
    if (evenement.target.closest("#infobulle") || evenement.target.closest(".repere")) return;
    fermerInfobulle();
  });
  rendu.addEventListener("scroll", suivreLeRepere, { passive: true });
  $("#defile").addEventListener("scroll", suivreLeRepere, { passive: true });
  window.addEventListener("resize", () => fermerInfobulle());
}

/* -------------------------------------------------------------------------
   Page « Mon dictionnaire »
   ------------------------------------------------------------------------- */

async function chargerDictionnaire() {
  const donnees = await appeler("dictionnaire");

  const mots = vider($("#mots"));
  donnees.mots.forEach((mot) => {
    mots.appendChild(jeton(mot, async () => {
      repondre(await appeler("retirer_mot", mot));
      chargerDictionnaire();
    }));
  });
  sinon(mots, "Aucun mot protégé pour l'instant.");
  compterDans("#nombre-mots", donnees.mots.length);

  const remplacements = vider($("#remplacements"));
  donnees.remplacements.forEach((r) => {
    const element = creer("li");
    element.appendChild(creer("code", null, r.de));
    const fleche = creer("span", "fleche");
    fleche.appendChild(icone("fleche", 14));
    element.appendChild(fleche);
    element.appendChild(creer("span", "vers", r.vers));
    element.appendChild(creer("span", "pousse"));
    element.appendChild(boutonRetirer(r.de, async () => {
      repondre(await appeler("retirer_remplacement", r.de));
      chargerDictionnaire();
    }));
    remplacements.appendChild(element);
  });
  sinon(remplacements, "Aucun remplacement enregistré.");
  compterDans("#nombre-remplacements", donnees.remplacements.length);
}

/* -------------------------------------------------------------------------
   Page « Vos fautes »
   ------------------------------------------------------------------------- */

async function chargerFautes() {
  const donnees = await appeler("fautes");

  const total = vider($("#total-corrections"));
  total.appendChild(creer("span", "total-nombre", NOMBRE.format(donnees.total)));
  total.appendChild(creer("span", "total-libelle",
    donnees.total > 1 ? "corrections appliquées" : "correction appliquée"));

  const liste = vider($("#frequentes"));
  const maximum = Math.max(1, ...donnees.frequentes.map((f) => f.compte));
  donnees.frequentes.forEach((faute, rang) => {
    const element = creer("li");
    element.appendChild(creer("span", "rang", String(rang + 1)));
    element.appendChild(creer("span", "mot", faute.mot));
    const piste = creer("div", "piste");
    const part = creer("div", "part");
    part.style.width = Math.max(4, (faute.compte / maximum) * 100) + "%";
    part.style.animationDelay = Math.min(rang * 45, 400) + "ms";
    piste.appendChild(part);
    element.appendChild(piste);
    element.appendChild(creer("span", "compte", NOMBRE.format(faute.compte)));
    liste.appendChild(element);
  });
  sinon(liste, "Rien encore. Corrigez un peu, revenez voir.");
}

/* Les trois reglages qui n'existaient que dans le fichier.

   Chacun s'enregistre des qu'il change : il n'y a pas de bouton
   « Enregistrer » dans cette fenetre, et il n'en faut pas un ici. */
function brancherReglagesFins() {
  lier("#touche-prediction", "touche_prediction", (champ) => champ.value);
  lier("#delai-oubli", "delai_oubli", (champ) => Number(champ.value));
  lier("#delai-copie", "delai_copie", (champ) => Number(champ.value));
}

function lier(selecteur, cle, lire) {
  const champ = $(selecteur);
  champ.value = etat.reglages[cle];
  champ.addEventListener("change", async () => {
    const valeur = lire(champ);
    // Un champ vide ou hors bornes rendrait « NaN », que Python prendrait
    // pour un reglage valide. On remet ce qui etait la.
    if (typeof valeur === "number" && !Number.isFinite(valeur)) {
      champ.value = etat.reglages[cle];
      return;
    }
    const reponse = repondre(await appeler("regler", cle, valeur));
    if (reponse.erreur) champ.value = etat.reglages[cle];
    else etat.reglages[cle] = valeur;
  });
}


/* -------------------------------------------------------------------------
   « Ce que Papote garde de vous »

   La promesse est ecrite partout ; celle-ci la rend verifiable. Les
   fichiers sont nommes, mesures, et le dossier s'ouvre d'un clic.
   ------------------------------------------------------------------------- */

async function chargerConfidentialite() {
  const donnees = await appeler("confidentialite");
  if (!donnees || donnees.erreur) return;

  $("#dossier-config").textContent = donnees.dossier || "";

  const liste = vider($("#fichiers-gardes"));
  (donnees.fichiers || []).forEach((fichier) => {
    const ligne = creer("li");
    const tuile = creer("span", "tuile petite");
    tuile.appendChild(icone("fichier", 15));
    ligne.appendChild(tuile);
    const gauche = creer("div", "fichier");
    gauche.appendChild(creer("div", "ligne-titre", fichier.nom));
    gauche.appendChild(creer("div", "aide", fichier.quoi));
    ligne.appendChild(gauche);
    ligne.appendChild(creer("span", "compte", poids(fichier.octets)));
    liste.appendChild(ligne);
  });
  sinon(liste, "Rien encore : Papote n'a pas eu besoin d'écrire.");
}

/* Le français met une virgule, et s'arrête au gigaoctet plutôt que
   d'annoncer « 1347.5 Mo », qu'il faut convertir de tête. */
function poids(octets) {
  if (octets < 1024) return octets + " o";
  if (octets < 1024 * 1024) return Math.round(octets / 1024) + " Ko";
  if (octets < 1024 * 1024 * 1024) {
    return virgule((octets / (1024 * 1024)).toFixed(0)) + " Mo";
  }
  return virgule((octets / (1024 * 1024 * 1024)).toFixed(1)) + " Go";
}

function virgule(nombre) {
  return String(nombre).replace(".", ",");
}


/* -------------------------------------------------------------------------
   Page « Applications »
   ------------------------------------------------------------------------- */

/* L'application au premier plan, proposee d'un clic.

   Elle servait de valeur par defaut a un champ vide : valider sans rien
   ecrire excluait une application qu'on n'avait pas nommee — et quand
   aucune n'etait detectee, c'etait « jeu.exe », le simple exemple du champ.
   Un clic explicite vaut mieux qu'un defaut invisible. */
function proposerLapplicationCourante(zone, champ, courante) {
  const ligne = vider($(zone));
  ligne.hidden = !courante;
  if (!courante) return;
  ligne.appendChild(document.createTextNode("Au premier plan : "));
  const bouton = creer("button", "proposition", courante);
  bouton.type = "button";
  bouton.addEventListener("click", () => {
    $(champ).value = courante;
    $(champ).focus();
  });
  ligne.appendChild(bouton);
}

async function chargerApplications() {
  const donnees = await appeler("applications");

  proposerLapplicationCourante("#courante-exclusion", "#exclusion",
                               donnees.courante);
  proposerLapplicationCourante("#courante-registre", "#registre-application",
                               donnees.courante);

  const exclues = vider($("#exclues"));
  donnees.exclues.forEach((application) => {
    exclues.appendChild(jeton(application, async () => {
      repondre(await appeler("reintegrer", application));
      chargerApplications();
    }));
  });
  sinon(exclues, "Papote corrige partout.");
  compterDans("#nombre-exclues", donnees.exclues.length);

  const registres = vider($("#registres-application"));
  donnees.registres.forEach((entree) => {
    const element = creer("li");
    element.appendChild(creer("code", null, entree.application));
    element.appendChild(creer("span", "pousse"));
    element.appendChild(creer("span", "etiquette accent", entree.registre));
    element.appendChild(boutonRetirer(entree.application, async () => {
      repondre(await appeler("retirer_registre_application", entree.application));
      chargerApplications();
    }));
    registres.appendChild(element);
  });
  sinon(registres, "Toutes suivent le registre par défaut.");
  compterDans("#nombre-registres", donnees.registres.length);
}

/* -------------------------------------------------------------------------
   Page « Réglages »
   ------------------------------------------------------------------------- */

function construireReglages() {
  const interrupteurs = vider($("#interrupteurs"));
  etat.interrupteurs.forEach((reglage) => {
    interrupteurs.appendChild(ligne(
      reglage.libelle, reglage.explication,
      bascule(etat.reglages[reglage.cle], async (actif) => {
        repondre(await appeler("regler", reglage.cle, actif));
      })));
  });

  // L'explication du ton choisi se lit sous le titre, plutot que dans une
  // info-bulle qu'il faut savoir aller chercher.
  segments($("#registre"), etat.registres, "registre", (cle) => {
    const choisi = etat.registres.find((r) => r.cle === cle);
    $("#registre-quoi").textContent = choisi
      ? choisi.nom + " : " + choisi.explication : "";
  });

  // La position de la bulle se choisit sur un petit ecran : un coin se
  // montre mieux qu'il ne se nomme.
  segments($("#position-bulle"), etat.positions_bulle, "position_bulle", (cle) => {
    const choisie = etat.positions_bulle.find((p) => p.cle === cle);
    $("#position-bulle-nom").textContent = choisie ? choisie.nom : "";
  });

  const raccourcis = vider($("#raccourcis"));
  etat.raccourcis.forEach((raccourci) => {
    raccourcis.appendChild(ligne(raccourci.libelle, null,
                                 champRaccourci(raccourci.cle, raccourci.libelle)));
  });

  const regles = vider($("#regles"));
  etat.regles_optionnelles.forEach((regle) => {
    regles.appendChild(ligne(regle.libelle, null,
      bascule(regle.actif, async (actif) => {
        repondre(await appeler("regler_regle", regle.cle, actif));
      })));
  });

  if (etat.demarrage_disponible) {
    $("#carte-demarrage").hidden = false;
    const zone = vider($("#demarrage"));
    zone.appendChild(ligne(
      "Lancer Papote avec Windows",
      "Il attend dans la zone de notification, sans rien faire de plus.",
      bascule(etat.demarrage_actif, async (actif) => {
        const reponse = repondre(await appeler("basculer_demarrage", actif));
        if (reponse.demarrage_actif !== undefined) {
          etat.demarrage_actif = reponse.demarrage_actif;
        }
      })));
  }

  montrerEtatMaj();
}

/* Une combinaison s'affiche en touches, comme sur le clavier. Elle reste
   enregistree dans l'orthographe qu'attend la bibliotheque de raccourcis :
   seul le dessin change. */
const NOMS_DE_TOUCHES = {
  ctrl: "Ctrl", alt: "Alt", shift: "Maj", windows: "Win", win: "Win",
  space: "Espace", enter: "Entrée", tab: "Tab", escape: "Échap",
  backspace: "Retour", delete: "Suppr", insert: "Inser",
};

function dessinerTouches(bouton, combinaison) {
  vider(bouton);
  if (!combinaison) { bouton.appendChild(creer("span", "aucun", "aucun")); return; }
  combinaison.split("+").forEach((touche) => {
    const nom = NOMS_DE_TOUCHES[touche]
      || (touche.length === 1 ? touche.toUpperCase()
                              : touche.charAt(0).toUpperCase() + touche.slice(1));
    bouton.appendChild(creer("kbd", null, nom));
  });
}

/* Un bouton qui attend la combinaison plutot que de la faire ecrire : taper
   « ctrl+alt+c » a la main suppose de connaitre l'orthographe exacte
   qu'attend la bibliotheque de raccourcis. */
function champRaccourci(cle, libelle) {
  const bouton = creer("button", "raccourci-champ");
  bouton.type = "button";
  bouton.setAttribute("aria-label", libelle + " : " + (etat.reglages[cle] || "aucun")
                      + ". Cliquez pour changer.");
  dessinerTouches(bouton, etat.reglages[cle]);
  let touches = [];
  let ecoute = false;

  const terminer = async () => {
    if (!ecoute) return;
    ecoute = false;
    bouton.classList.remove("ecoute");
    document.removeEventListener("keydown", enfoncee, true);
    document.removeEventListener("keyup", relachee, true);
    const combinaison = touches.join("+");
    dessinerTouches(bouton, combinaison || etat.reglages[cle]);
    if (combinaison && combinaison !== etat.reglages[cle]) {
      etat.reglages[cle] = combinaison;
      bouton.setAttribute("aria-label", libelle + " : " + combinaison
                          + ". Cliquez pour changer.");
      repondre(await appeler("regler", cle, combinaison));
    }
  };

  const enfoncee = (evenement) => {
    evenement.preventDefault();
    if (evenement.key === "Escape") { touches = []; terminer(); return; }
    const modificateurs = [];
    if (evenement.ctrlKey) modificateurs.push("ctrl");
    if (evenement.altKey) modificateurs.push("alt");
    if (evenement.shiftKey) modificateurs.push("shift");
    if (evenement.key.length === 1) modificateurs.push(evenement.key.toLowerCase());
    else if (!/^(Control|Alt|Shift|Meta)$/.test(evenement.key)) {
      modificateurs.push(evenement.key.toLowerCase());
    }
    touches = modificateurs;
    if (touches.length) dessinerTouches(bouton, touches.join("+"));
  };

  const relachee = (evenement) => {
    evenement.preventDefault();
    // On valide des qu'une vraie touche accompagne les modificateurs.
    if (touches.some((t) => !/^(ctrl|alt|shift)$/.test(t))) terminer();
  };

  bouton.addEventListener("click", () => {
    if (ecoute) return;
    ecoute = true;
    touches = [];
    vider(bouton).appendChild(creer("span", "aucun", "Appuyez…"));
    bouton.classList.add("ecoute");
    document.addEventListener("keydown", enfoncee, true);
    document.addEventListener("keyup", relachee, true);
  });
  // Partir ailleurs, c'est renoncer : sans cela, la prochaine touche
  // tapee n'importe ou devenait le raccourci.
  bouton.addEventListener("blur", () => { touches = []; terminer(); });
  return bouton;
}

/* -------------------------------------------------------------------------
   Mises a jour
   ------------------------------------------------------------------------- */

function montrerEtatMaj() {
  const etatMaj = etat.maj || {};
  const annonce = $("#annonce-maj");

  if (!etatMaj.compilee) {
    $("#maj-etat").textContent = "Lancé depuis les sources";
    $("#maj-detail").textContent = "« git pull » fait le travail.";
    $("#verifier-maj").hidden = true;
    annonce.hidden = true;
    return;
  }

  const bouton = $("#verifier-maj");
  bouton.hidden = false;
  if (etatMaj.prete) {
    const numero = etatMaj.numero ? "Version " + etatMaj.numero + " prête"
                                  : "Mise à jour prête";
    $("#maj-etat").textContent = numero;
    $("#maj-detail").textContent = "Redémarrez pour l'installer.";
    // Chercher une version alors qu'une autre attend déjà ne mène nulle
    // part : le bouton propose donc la seule chose qui reste à faire.
    bouton.textContent = "Redémarrer pour installer";
    bouton.classList.add("principal");
    $("#annonce-titre").textContent = numero;
    if (!annonce.dataset.renvoyee) annonce.hidden = false;
  } else {
    $("#maj-etat").textContent = "Version " + etat.version;
    $("#maj-detail").textContent = "Vous êtes à jour.";
    bouton.textContent = "Vérifier maintenant";
    bouton.classList.remove("principal");
    annonce.hidden = true;
  }
}

async function chargerJournal() {
  const journal = await appeler("journal");
  const zone = $("#journal");
  zone.textContent = journal.contenu || "Rien à signaler. C'est bon signe.";
  zone.classList.toggle("vide", !journal.contenu);
  zone.title = journal.chemin || "";
}

/* -------------------------------------------------------------------------
   Demarrage
   ------------------------------------------------------------------------- */

/* Copier, et le dire sur le bouton meme : c'est la qu'on regarde. */
async function copierLeTexte() {
  const texte = $("#champ").value;
  if (!texte) return;
  try {
    await navigator.clipboard.writeText(texte);
  } catch (e) {
    // Le moteur refuse parfois le presse-papiers sans geste de
    // l'utilisateur. Le champ peut etre masque par le rendu : on passe par
    // un double, invisible.
    const double = creer("textarea", "hors-champ");
    double.value = texte;
    document.body.appendChild(double);
    double.select();
    document.execCommand("copy");
    double.remove();
  }
  dire("Texte copié dans le presse-papiers.", "succes");
  const bouton = $("#copier");
  const contenu = Array.from(bouton.childNodes);
  bouton.replaceChildren(icone("coche", 16), document.createTextNode("Copié"));
  bouton.classList.add("fait");
  setTimeout(() => {
    bouton.replaceChildren(...contenu);
    bouton.classList.remove("fait");
  }, 1600);
}

function brancher() {
  $("#corriger").addEventListener("click", corriger);
  brancherLeTexte();

  document.addEventListener("keydown", (evenement) => {
    if (evenement.key === "Escape" && repereOuvert) {
      evenement.preventDefault();
      fermerInfobulle(true);
      return;
    }
    if (pageActive() !== "corriger") return;
    const raccourci = evenement.ctrlKey || evenement.metaKey;
    if (raccourci && evenement.key === "Enter") {
      evenement.preventDefault();
      corriger();
    }
    // Ctrl+Z ne defait que ce que le programme a ecrit. Tant qu'il n'y a
    // rien a rendre, ou que l'on a tape depuis, la touche garde son role :
    // defaire la frappe.
    if (raccourci && evenement.key === "z" && !evenement.shiftKey
        && etatsPrecedents.length && !relecturePerimee()) {
      evenement.preventDefault();
      annulerLaDerniere();
    }
  });

  $("#copier").addEventListener("click", copierLeTexte);

  $("#annuler").addEventListener("click", annulerLaDerniere);

  $("#ouvrir-dossier").addEventListener("click", async () => {
    repondre(await appeler("ouvrir_le_dossier"));
  });

  $("#vider").addEventListener("click", () => {
    if ($("#champ").value) retenirLetat();
    ecrire("");
    relecture = null;
    montrerRelecture();
    passerEnEdition();
  });

  $("#forme-mot").addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    const champ = $("#mot");
    const reponse = repondre(await appeler("ajouter_mot", champ.value));
    if (!reponse.erreur) { champ.value = ""; chargerDictionnaire(); }
    champ.focus();
  });

  $("#forme-remplacement").addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    const de = $("#remplacement-de");
    const vers = $("#remplacement-vers");
    const reponse = repondre(
      await appeler("ajouter_remplacement", de.value, vers.value));
    if (!reponse.erreur) { de.value = ""; vers.value = ""; chargerDictionnaire(); }
    de.focus();
  });

  $("#forme-exclusion").addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    const champ = $("#exclusion");
    const reponse = repondre(await appeler("exclure", champ.value));
    if (!reponse.erreur) { champ.value = ""; chargerApplications(); }
  });

  $("#forme-registre").addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    const champ = $("#registre-application");
    const reponse = repondre(await appeler(
      "registre_application", champ.value, "soutenu"));
    if (!reponse.erreur) { champ.value = ""; chargerApplications(); }
  });

  armer("#effacer-historique", async () => {
    repondre(await appeler("effacer_historique"));
    chargerFautes();
  });

  $("#verifier-maj").addEventListener("click", async () => {
    // Une version téléchargée attend : ce bouton redémarre, il ne cherche
    // plus.
    if ((etat.maj || {}).prete) {
      repondre(await appeler("redemarrer"));
      return;
    }
    const bouton = $("#verifier-maj");
    bouton.disabled = true;
    bouton.textContent = "Recherche…";
    const reponse = repondre(await appeler("verifier_maj"));
    bouton.disabled = false;
    if (reponse.maj) etat.maj = reponse.maj;
    // C'est « montrerEtatMaj » qui repose le libellé : il sait lequel.
    montrerEtatMaj();
  });

  $("#maj-redemarrer").addEventListener("click", async () => {
    repondre(await appeler("redemarrer"));
  });

  $("#maj-plus-tard").addEventListener("click", () => {
    const annonce = $("#annonce-maj");
    annonce.hidden = true;
    annonce.dataset.renvoyee = "1";
    dire("La mise à jour s'installera au prochain démarrage.");
  });

  $("#copier-journal").addEventListener("click", async () => {
    const journal = await appeler("journal");
    try {
      await navigator.clipboard.writeText(journal.contenu || "");
      dire("Journal copié.", "succes");
    } catch (e) {
      dire("Copie impossible depuis cette fenêtre.", "alerte");
    }
  });

  armer("#vider-journal", async () => {
    repondre(await appeler("vider_journal"));
    chargerJournal();
  });

  // L'en-tete se detache du contenu des qu'il defile dessous.
  $("#defile").addEventListener("scroll", () => {
    $("#principal").classList.toggle("defilee", $("#defile").scrollTop > 2);
  }, { passive: true });
}

function construireNavigation() {
  const nav = vider($("#nav"));
  etat.pages.forEach((page) => {
    const entree = creer("button", "entree");
    entree.type = "button";
    entree.dataset.page = page.cle;
    entree.title = page.nom;
    entree.appendChild(icone(page.icone, 18));
    entree.appendChild(creer("span", "entree-nom", page.nom));
    entree.addEventListener("click", () => afficher(page.cle));
    nav.appendChild(entree);
  });

  // Les fleches parcourent la colonne, comme dans n'importe quelle liste.
  nav.addEventListener("keydown", (evenement) => {
    const pas = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[evenement.key];
    if (!pas) return;
    const entrees = Array.from(nav.querySelectorAll(".entree"));
    const rang = entrees.indexOf(document.activeElement);
    if (rang < 0) return;
    evenement.preventDefault();
    entrees[(rang + pas + entrees.length) % entrees.length].focus();
  });
}

async function demarrer() {
  etat = await appeler("demarrer");
  if (etat.erreur) { dire(etat.erreur, "alerte"); return; }

  decorer();
  etiqueterCorriger(false);

  // Le logo vient de Python en SVG : c'est le meme trace que l'icone du
  // programme et que les images de l'installateur.
  $("#marque-logo").innerHTML = etat.logo;
  $("#version").textContent = etat.version;

  construireNavigation();
  construireReglages();
  brancherReglagesFins();
  brancher();
  afficher("corriger");
  $("#champ").focus();
  document.body.classList.add("pret");

  // Le raccourci de relecture ouvre la fenetre avec la selection dedans.
  // On la corrige tout de suite : c'est ce qu'on venait demander.
  if (etat.texte_a_relire) {
    ecrire(etat.texte_a_relire);
    corriger();
  }
}


demarrer();
