(() => {
  const storageKey = "le-bon-prenom:return-url";

  function getAllowedOrigin(value) {
    if (!value) {
      return null;
    }

    try {
      const url = new URL(value, window.location.href);
      const hostname = url.hostname.toLowerCase();
      const isProduction =
        url.protocol === "https:" &&
        (hostname === "le-bon-prenom.fr" || hostname === "www.le-bon-prenom.fr");
      const isLocal =
        url.protocol === "http:" &&
        (hostname === "localhost" || hostname === "127.0.0.1") &&
        url.port === "5173";

      return isProduction || isLocal ? url.origin : null;
    } catch {
      return null;
    }
  }

  function configureReturnUrl(link) {
    let storedOrigin = null;

    try {
      storedOrigin = getAllowedOrigin(sessionStorage.getItem(storageKey));
    } catch {
      storedOrigin = null;
    }

    const queryRedirectUri = new URLSearchParams(window.location.search).get("redirect_uri");
    const returnOrigin =
      getAllowedOrigin(queryRedirectUri) ||
      getAllowedOrigin(document.referrer) ||
      storedOrigin ||
      getAllowedOrigin(link.href);

    if (!returnOrigin) {
      link.hidden = true;
      return;
    }

    link.href = `${returnOrigin}/`;

    try {
      sessionStorage.setItem(storageKey, returnOrigin);
    } catch {
      // Le lien reste fonctionnel si le stockage de session est indisponible.
    }
  }

  function placeReturnButton() {
    const link = document.getElementById("lbp-home-return");
    const returnBlock = document.querySelector("[data-lbp-home-return]");
    const loginCard =
      document.querySelector(".pf-v5-c-login__main") ||
      document.querySelector(".card-pf") ||
      document.getElementById("kc-content")?.closest("main");

    if (!link || !returnBlock) {
      return false;
    }

    configureReturnUrl(link);

    if (!loginCard) {
      return false;
    }

    // Le footer Keycloak est normalement rendu hors de la carte. On déplace
    // explicitement le bloc comme dernier enfant de la carte, après le bloc
    // « Créer mon espace » sur la connexion et après le formulaire d'inscription.
    if (returnBlock.parentElement !== loginCard) {
      loginCard.appendChild(returnBlock);
    }

    returnBlock.dataset.lbpPlaced = "true";
    return true;
  }

  function initialize() {
    if (placeReturnButton()) {
      return;
    }

    // Sécurité pour les variantes de page dont le contenu serait ajouté après
    // l'exécution initiale du script.
    const observer = new MutationObserver(() => {
      if (placeReturnButton()) {
        observer.disconnect();
      }
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });

    window.setTimeout(() => observer.disconnect(), 5000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
