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

/* Les icones de la colonne. Dessinees ici en traits de 1,5 pixel, a la meme
   grille de 24 : des icones d'epaisseurs differentes se remarquent tout de
   suite, meme sans savoir pourquoi. */
const ICONES = {
  crayon: "M4 20h4L20 8a2.8 2.8 0 0 0-4-4L4 16v4Z M13.5 6.5l4 4",
  livre: "M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5v-13Z "
       + "M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5v-13Z",
  barres: "M5 20V11 M12 20V4 M19 20v-6",
  fenetre: "M3.5 6.5A2 2 0 0 1 5.5 4.5h13a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-13"
         + "a2 2 0 0 1-2-2v-11Z M3.5 9h17",
  micro: "M12 3.5a2.6 2.6 0 0 1 2.6 2.6v5.4a2.6 2.6 0 1 1-5.2 0V6.1"
       + "A2.6 2.6 0 0 1 12 3.5Z M5.8 10.6a6.2 6.2 0 0 0 12.4 0 M12 16.8V20"
       + " M9 20h6",
  reglages: "M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z "
          + "M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1"
          + "a1.6 1.6 0 0 0-2.7 1.1 2 2 0 1 1-4 0 1.6 1.6 0 0 0-2.7-1.1"
          + "l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3.4 14a2 2 0 1 1 0-4"
          + "a1.6 1.6 0 0 0 1.1-2.7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 10 3.4"
          + "a2 2 0 1 1 4 0 1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1"
          + "A1.6 1.6 0 0 0 20.6 10a2 2 0 1 1 0 4 1.6 1.6 0 0 0-1.2 1Z",
};

function icone(nom) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "17");
  svg.setAttribute("height", "17");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.6");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const trace = document.createElementNS("http://www.w3.org/2000/svg", "path");
  trace.setAttribute("d", ICONES[nom] || ICONES.reglages);
  svg.appendChild(trace);
  return svg;
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
  toast.textContent = message;
  toast.className = "toast visible" + (ton ? " " + ton : "");
  clearTimeout(minuterieToast);
  minuterieToast = setTimeout(() => toast.classList.remove("visible"), 4200);
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

function bascule(actif, surChangement) {
  const bouton = creer("button", "bascule");
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
   diverger. */
function segments(zone, choix, reglage) {
  vider(zone);
  choix.forEach((option) => {
    const bouton = creer("button", "segment", option.nom);
    if (option.explication) bouton.title = option.explication;
    bouton.setAttribute("aria-pressed",
                        String(etat.reglages[reglage] === option.cle));
    bouton.addEventListener("click", async () => {
      etat.reglages[reglage] = option.cle;
      zone.querySelectorAll(".segment").forEach((autre) => {
        autre.setAttribute("aria-pressed", String(autre === bouton));
      });
      repondre(await appeler("regler", reglage, option.cle));
    });
    zone.appendChild(bouton);
  });
}


function ligne(titre, explication, controle) {
  const rangee = creer("div", "ligne-action");
  const textes = creer("div");
  textes.appendChild(creer("div", "ligne-titre", titre));
  if (explication) textes.appendChild(creer("div", "aide", explication));
  rangee.appendChild(textes);
  rangee.appendChild(controle);
  return rangee;
}

function jeton(texte, surRetrait) {
  const element = creer("li", "jeton");
  element.appendChild(document.createTextNode(texte));
  const croix = creer("button", null, "×");
  croix.title = "Retirer";
  croix.setAttribute("aria-label", "Retirer " + texte);
  croix.addEventListener("click", surRetrait);
  element.appendChild(croix);
  return element;
}

function sinon(liste, message) {
  if (!liste.childElementCount) liste.appendChild(creer("li", "vide", message));
}

/* -------------------------------------------------------------------------
   Navigation
   ------------------------------------------------------------------------- */

const RAFRAICHIR = {
  dictionnaire: chargerDictionnaire,
  fautes: chargerFautes,
  applications: chargerApplications,
  dicter: chargerDictee,
  reglages: chargerJournal,
};

function afficher(cle) {
  const page = etat.pages.find((p) => p.cle === cle) || etat.pages[0];
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
  if (RAFRAICHIR[page.cle]) RAFRAICHIR[page.cle]();
}

/* -------------------------------------------------------------------------
   Page « Corriger »
   ------------------------------------------------------------------------- */

function compter() {
  const texte = $("#champ").value.trim();
  const mots = texte ? texte.split(/\s+/).length : 0;
  $("#compteur").textContent = mots ? mots + (mots > 1 ? " mots" : " mot") : "";
}

async function corriger() {
  const champ = $("#champ");
  const bouton = $("#corriger");
  if (!champ.value.trim()) return;

  bouton.disabled = true;
  bouton.textContent = "…";
  const reponse = repondre(await appeler("corriger", champ.value));
  bouton.disabled = false;
  vider(bouton);
  bouton.appendChild(document.createTextNode("Corriger"));
  bouton.appendChild(creer("kbd", null, "Ctrl ↵"));

  if (reponse.erreur) return;
  champ.value = reponse.texte;
  compter();
  montrerCorrections(reponse.corrections);
  montrerInconnus(reponse.inconnus);

  if (!reponse.corrections.length && !reponse.inconnus.length) {
    dire("Aucune faute trouvée.", "succes");
  } else if (reponse.corrections.length) {
    const n = reponse.corrections.length;
    dire(n + (n > 1 ? " corrections appliquées." : " correction appliquée."),
         "succes");
  }
}

function montrerCorrections(corrections) {
  const zone = vider($("#corrections"));
  zone.hidden = !corrections.length;
  corrections.forEach((correction, rang) => {
    const puce = creer("span", "correction");
    puce.style.animationDelay = Math.min(rang * 28, 320) + "ms";
    puce.title = correction.message || "";
    puce.appendChild(creer("del", null, correction.avant));
    puce.appendChild(creer("ins", null, correction.apres));
    zone.appendChild(puce);
  });
}

/* Les mots dont le correcteur n'est pas sur. Il se tait plutot que d'inventer
   une faute ; c'est ici qu'ils reviennent, avec de quoi choisir. */
function montrerInconnus(inconnus) {
  const zone = vider($("#inconnus"));
  zone.hidden = !inconnus.length;
  inconnus.forEach((inconnu, rang) => {
    const rangee = creer("div", "inconnu");
    rangee.style.animationDelay = Math.min(rang * 40, 320) + "ms";
    rangee.appendChild(creer("span", "inconnu-mot", inconnu.mot));

    inconnu.propositions.forEach((proposition) => {
      const bouton = creer("button", "bouton minuscule", proposition);
      bouton.addEventListener("click", async () => {
        const reponse = repondre(
          await appeler("remplacer", $("#champ").value, inconnu.mot, proposition));
        if (reponse.erreur) return;
        $("#champ").value = reponse.texte;
        compter();
        montrerInconnus(reponse.inconnus);
        dire("« " + inconnu.mot + " » remplacé par « " + proposition + " ».",
             "succes");
      });
      rangee.appendChild(bouton);
    });

    const garder = creer("button", "bouton discret minuscule",
                         "garder « " + inconnu.mot + " »");
    garder.addEventListener("click", async () => {
      repondre(await appeler("ajouter_mot", inconnu.mot));
      const reponse = await appeler("corriger", $("#champ").value);
      if (!reponse.erreur) montrerInconnus(reponse.inconnus);
    });
    rangee.appendChild(garder);
    zone.appendChild(rangee);
  });
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

  const remplacements = vider($("#remplacements"));
  donnees.remplacements.forEach((r) => {
    const element = creer("li");
    element.appendChild(creer("code", null, r.de));
    element.appendChild(creer("span", "fleche", "→"));
    element.appendChild(creer("span", null, r.vers));
    element.appendChild(creer("span", "pousse"));
    const retirer = creer("button", "bouton discret minuscule", "Retirer");
    retirer.addEventListener("click", async () => {
      repondre(await appeler("retirer_remplacement", r.de));
      chargerDictionnaire();
    });
    element.appendChild(retirer);
    remplacements.appendChild(element);
  });
  sinon(remplacements, "Aucun remplacement enregistré.");
}

/* -------------------------------------------------------------------------
   Page « Vos fautes »
   ------------------------------------------------------------------------- */

async function chargerFautes() {
  const donnees = await appeler("fautes");

  const total = vider($("#total-corrections"));
  total.appendChild(document.createTextNode(String(donnees.total)));
  total.appendChild(creer("small", null,
    donnees.total > 1 ? "corrections appliquées" : "correction appliquée"));

  const liste = vider($("#frequentes"));
  const maximum = Math.max(1, ...donnees.frequentes.map((f) => f.compte));
  donnees.frequentes.forEach((faute, rang) => {
    const element = creer("li");
    element.appendChild(creer("span", "mot", faute.mot));
    const piste = creer("div", "piste");
    const part = creer("div", "part");
    part.style.width = Math.max(4, (faute.compte / maximum) * 100) + "%";
    part.style.animationDelay = Math.min(rang * 45, 400) + "ms";
    piste.appendChild(part);
    element.appendChild(piste);
    element.appendChild(creer("span", "compte", String(faute.compte)));
    liste.appendChild(element);
  });
  sinon(liste, "Rien encore. Corrigez un peu, revenez voir.");
}

/* -------------------------------------------------------------------------
   Page « Applications »
   ------------------------------------------------------------------------- */

async function chargerApplications() {
  const donnees = await appeler("applications");

  if (donnees.courante) {
    $("#exclusion").placeholder = donnees.courante;
    $("#registre-application").placeholder = donnees.courante;
  }

  const exclues = vider($("#exclues"));
  donnees.exclues.forEach((application) => {
    exclues.appendChild(jeton(application, async () => {
      repondre(await appeler("reintegrer", application));
      chargerApplications();
    }));
  });
  sinon(exclues, "Papote corrige partout.");

  const registres = vider($("#registres-application"));
  donnees.registres.forEach((entree) => {
    const element = creer("li");
    element.appendChild(creer("code", null, entree.application));
    element.appendChild(creer("span", null, entree.registre));
    element.appendChild(creer("span", "pousse"));
    const retirer = creer("button", "bouton discret minuscule", "Retirer");
    retirer.addEventListener("click", async () => {
      repondre(await appeler("retirer_registre_application", entree.application));
      chargerApplications();
    });
    element.appendChild(retirer);
    registres.appendChild(element);
  });
  sinon(registres, "Toutes suivent le registre par défaut.");
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

  segments($("#registre"), etat.registres, "registre");

  segments($("#position-bulle"), etat.positions_bulle, "position_bulle");

  const raccourcis = vider($("#raccourcis"));
  etat.raccourcis.forEach((raccourci) => {
    raccourcis.appendChild(ligne(raccourci.libelle, null,
                                 champRaccourci(raccourci.cle)));
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

/* Un bouton qui attend la combinaison plutot que de la faire ecrire : taper
   « ctrl+alt+c » a la main suppose de connaitre l'orthographe exacte
   qu'attend la bibliotheque de raccourcis. */
function champRaccourci(cle) {
  const bouton = creer("button", "bouton raccourci-champ",
                       etat.reglages[cle] || "aucun");
  let touches = [];

  const terminer = async () => {
    bouton.classList.remove("ecoute");
    document.removeEventListener("keydown", enfoncee, true);
    document.removeEventListener("keyup", relachee, true);
    const combinaison = touches.join("+");
    bouton.textContent = combinaison || etat.reglages[cle] || "aucun";
    if (combinaison && combinaison !== etat.reglages[cle]) {
      etat.reglages[cle] = combinaison;
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
    bouton.textContent = touches.join("+") || "…";
  };

  const relachee = (evenement) => {
    evenement.preventDefault();
    // On valide des qu'une vraie touche accompagne les modificateurs.
    if (touches.some((t) => !/^(ctrl|alt|shift)$/.test(t))) terminer();
  };

  bouton.addEventListener("click", () => {
    touches = [];
    bouton.textContent = "Appuyez…";
    bouton.classList.add("ecoute");
    document.addEventListener("keydown", enfoncee, true);
    document.addEventListener("keyup", relachee, true);
  });
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

  $("#verifier-maj").hidden = false;
  if (etatMaj.prete) {
    const numero = etatMaj.numero ? "Version " + etatMaj.numero + " prête"
                                  : "Mise à jour prête";
    $("#maj-etat").textContent = numero;
    $("#maj-detail").textContent = "Redémarrez pour l'installer.";
    $("#annonce-titre").textContent = numero;
    if (!annonce.dataset.renvoyee) annonce.hidden = false;
  } else {
    $("#maj-etat").textContent = "Version " + etat.version;
    $("#maj-detail").textContent = "Vous êtes à jour.";
    annonce.hidden = true;
  }
}

async function chargerJournal() {
  const journal = await appeler("journal");
  const zone = $("#journal");
  zone.textContent = journal.contenu || "Rien à signaler. C'est bon signe.";
  zone.title = journal.chemin || "";
}

/* -------------------------------------------------------------------------
   Demarrage
   ------------------------------------------------------------------------- */

function brancher() {
  $("#corriger").addEventListener("click", corriger);
  $("#champ").addEventListener("input", compter);
  document.addEventListener("keydown", (evenement) => {
    if ((evenement.ctrlKey || evenement.metaKey) && evenement.key === "Enter") {
      evenement.preventDefault();
      corriger();
    }
  });

  $("#copier").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("#champ").value);
      dire("Texte copié dans le presse-papiers.", "succes");
    } catch (e) {
      // Le moteur refuse parfois le presse-papiers sans geste de l'utilisateur.
      $("#champ").select();
      document.execCommand("copy");
      dire("Texte copié.", "succes");
    }
  });

  $("#vider").addEventListener("click", () => {
    $("#champ").value = "";
    compter();
    montrerCorrections([]);
    montrerInconnus([]);
    $("#champ").focus();
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
    const reponse = repondre(
      await appeler("exclure", champ.value || champ.placeholder));
    if (!reponse.erreur) { champ.value = ""; chargerApplications(); }
  });

  $("#forme-registre").addEventListener("submit", async (evenement) => {
    evenement.preventDefault();
    const champ = $("#registre-application");
    const reponse = repondre(await appeler(
      "registre_application", champ.value || champ.placeholder, "soutenu"));
    if (!reponse.erreur) { champ.value = ""; chargerApplications(); }
  });

  $("#effacer-historique").addEventListener("click", async () => {
    repondre(await appeler("effacer_historique"));
    chargerFautes();
  });

  $("#verifier-maj").addEventListener("click", async () => {
    const bouton = $("#verifier-maj");
    bouton.disabled = true;
    bouton.textContent = "Recherche…";
    const reponse = repondre(await appeler("verifier_maj"));
    bouton.disabled = false;
    bouton.textContent = "Vérifier maintenant";
    if (reponse.maj) { etat.maj = reponse.maj; montrerEtatMaj(); }
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

  $("#vider-journal").addEventListener("click", async () => {
    repondre(await appeler("vider_journal"));
    chargerJournal();
  });
}

async function demarrer() {
  etat = await appeler("demarrer");
  if (etat.erreur) { dire(etat.erreur, "alerte"); return; }

  // Le logo vient de Python en SVG : c'est le meme trace que l'icone du
  // programme et que les images de l'installateur.
  $("#marque-logo").innerHTML = etat.logo;
  $("#version").textContent = etat.version;

  const nav = vider($("#nav"));
  etat.pages.forEach((page) => {
    const entree = creer("button", "entree");
    entree.dataset.page = page.cle;
    entree.appendChild(icone(page.icone));
    entree.appendChild(creer("span", null, page.nom));
    entree.addEventListener("click", () => afficher(page.cle));
    nav.appendChild(entree);
  });

  construireReglages();
  brancher();
  brancherDictee();
  afficher("corriger");
  $("#champ").focus();
}


/* -------------------------------------------------------------------------
   Dicter

   Deux modes, une seule page. Tant que les modeles ne sont pas la, la page
   ne montre que ce qu'il faut faire pour qu'ils y soient — un bouton qui
   echouerait vaut moins qu'une phrase qui explique.
   ------------------------------------------------------------------------- */

let minuterieDictee = null;

async function chargerDictee() {
  const etatDictee = await appeler("etat_dictee");
  if (!etatDictee || etatDictee.erreur) return;
  montrerDictee(etatDictee);
}

function montrerDictee(d) {
  const manque = Object.entries(d.disponible || {})
    .filter(([, present]) => !present)
    .map(([nom]) => nom);

  $("#dictee-indisponible").hidden = manque.length === 0;
  if (manque.length) {
    $("#dictee-pourquoi").textContent =
      "Cette installation de Papote n'embarque pas " + manque.join(" ni ")
      + ". La dictée demande la version installée depuis Papote.msi.";
  }

  const modeles = d.modeles || [];
  const aInstaller = modeles.filter((m) => !m.installe);
  $("#dictee-installation").hidden = manque.length > 0 || aInstaller.length === 0;
  const liste = vider($("#dictee-modeles"));
  modeles.forEach((m) => {
    const ligne = creer("li", m.installe ? "fait" : null);
    ligne.textContent = (m.installe ? "✓ " : "· ") + m.role
      + " — " + Math.round(m.taille / 1e6) + " Mo";
    liste.appendChild(ligne);
  });

  $("#dictee-commandes").hidden = manque.length > 0;
  $("#dicter-demarrer").hidden = d.en_cours;
  $("#reunion-demarrer").hidden = d.en_cours;
  $("#dicter-arreter").hidden = !d.en_cours;
  $("#dictee-boucle-ligne").hidden = d.en_cours;
  $("#dictee-etat").textContent = d.en_cours
    ? (d.reunion ? "Réunion en cours…" : "Dictée en cours…")
    : (d.erreur || "");

  const tours = d.tours || [];
  $("#dictee-resultat").hidden = tours.length === 0;
  const zone = vider($("#dictee-tours"));
  tours.forEach((tour) => {
    const bloc = creer("div", "tour");
    const nom = creer("button", "locuteur", tour.locuteur);
    nom.title = "Cliquez pour renommer cette voix";
    nom.addEventListener("click", () => renommerLocuteur(tour.locuteur));
    bloc.appendChild(nom);
    bloc.appendChild(creer("p", null, tour.texte));
    zone.appendChild(bloc);
  });
}

async function renommerLocuteur(ancien) {
  const nouveau = window.prompt("Qui est « " + ancien + " » ?", ancien);
  if (!nouveau || nouveau === ancien) return;
  await appeler("renommer_locuteur", ancien, nouveau);
  chargerDictee();
}

function suivreLaDictee(actif) {
  clearInterval(minuterieDictee);
  minuterieDictee = actif ? setInterval(chargerDictee, 1500) : null;
}

function brancherDictee() {
  $("#installer-modeles").addEventListener("click", async (evenement) => {
    const bouton = evenement.currentTarget;
    bouton.disabled = true;
    $("#dictee-avancement").textContent = "Téléchargement…";
    const reponse = await appeler("installer_modeles", true);
    bouton.disabled = false;
    $("#dictee-avancement").textContent = "";
    dire(reponse && reponse.ok ? (reponse.message || "Installé.")
                               : (reponse && reponse.erreur) || "Échec.");
    chargerDictee();
  });

  const lancer = async (reunion) => {
    const boucle = reunion && $("#dictee-boucle").checked;
    const reponse = await appeler("commencer_dictee", reunion, boucle);
    if (reponse && reponse.avertissement) dire(reponse.avertissement);
    else if (!reponse || !reponse.ok) dire((reponse && reponse.erreur) || "Échec.");
    suivreLaDictee(Boolean(reponse && reponse.ok));
    chargerDictee();
  };
  $("#dicter-demarrer").addEventListener("click", () => lancer(false));
  $("#reunion-demarrer").addEventListener("click", () => lancer(true));

  $("#dicter-arreter").addEventListener("click", async () => {
    await appeler("arreter_dictee");
    suivreLaDictee(false);
    chargerDictee();
  });

  $("#dictee-compte-rendu").addEventListener("click", async () => {
    const reponse = await appeler("compte_rendu", $("#dictee-titre").value, "");
    if (!reponse || !reponse.ok) {
      dire((reponse && reponse.erreur) || "Échec.");
      return;
    }
    /* Le compte rendu part dans la page « Corriger » : c'est là qu'on relit
       et qu'on copie, et il n'y a pas de raison d'avoir deux éditeurs. */
    $("#champ").value = reponse.texte;
    afficher("corriger");
    dire("Compte rendu prêt — relisez-le avant de l'envoyer.");
  });

  $("#dictee-copier").addEventListener("click", async () => {
    const reponse = await appeler("compte_rendu", $("#dictee-titre").value, "");
    if (!reponse || !reponse.ok) {
      dire((reponse && reponse.erreur) || "Échec.");
      return;
    }
    try {
      await navigator.clipboard.writeText(reponse.texte);
      dire("Compte rendu copié.");
    } catch (e) {
      dire("La copie a échoué.");
    }
  });

  $("#dictee-oublier").addEventListener("click", async () => {
    await appeler("oublier_dictee");
    suivreLaDictee(false);
    chargerDictee();
  });
}

demarrer();
