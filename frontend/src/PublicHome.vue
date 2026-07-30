<script setup lang="ts">
import { ref } from 'vue'

import keycloak from './auth/keycloak'

type RedirectAction = 'login' | 'register'

const redirectingTo = ref<RedirectAction | null>(null)
const errorMessage = ref('')

async function redirectToKeycloak(action: RedirectAction) {
  redirectingTo.value = action
  errorMessage.value = ''

  try {
    const options = {
      redirectUri: window.location.origin,
      locale: 'fr',
    }

    if (action === 'register') {
      await keycloak.register(options)
      return
    }

    await keycloak.login(options)
  } catch (error) {
    console.error('Échec de la redirection vers Keycloak :', error)

    errorMessage.value =
      action === 'register'
        ? "Impossible d'ouvrir la création de compte."
        : "Impossible d'ouvrir la page de connexion."

    redirectingTo.value = null
  }
}

function login() {
  void redirectToKeycloak('login')
}

function register() {
  void redirectToKeycloak('register')
}
</script>

<template>
  <main class="public-page">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Accueil Le Bon Prénom">
        <span class="brand-mark">LBP</span>

        <span>
          <strong>Le Bon Prénom</strong>
          <small>Trouvez-le ensemble</small>
        </span>
      </a>

      <button
        type="button"
        class="header-login-button"
        :disabled="redirectingTo !== null"
        @click="login"
      >
        Se connecter
      </button>
    </header>

    <section class="hero">
      <div class="hero-content">
        <p class="eyebrow">Le choix qui vous rassemble</p>

        <h1>
          Trouvez le prénom qui vous ressemble,
          <span>ensemble.</span>
        </h1>

        <p class="hero-description">
          Créez votre espace, partagez vos préférences et découvrez les prénoms qui font
          l’unanimité.
        </p>

        <div class="hero-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="redirectingTo !== null"
            @click="register"
          >
            {{ redirectingTo === 'register' ? 'Ouverture du formulaire…' : 'Créer mon compte' }}
          </button>

          <button
            type="button"
            class="secondary-button"
            :disabled="redirectingTo !== null"
            @click="login"
          >
            {{ redirectingTo === 'login' ? 'Connexion…' : 'J’ai déjà un compte' }}
          </button>
        </div>

        <p v-if="errorMessage" class="error-message" role="alert">
          {{ errorMessage }}
        </p>

        <div class="trust-line">
          <span class="trust-icon">✓</span>

          <span> Connexion sécurisée et mots de passe protégés par Keycloak </span>
        </div>
      </div>

      <div class="preview" aria-hidden="true">
        <div class="decorative-circle circle-one"></div>
        <div class="decorative-circle circle-two"></div>

        <article class="preview-card main-card">
          <div class="card-topline">
            <span class="preview-logo">LBP</span>
            <span class="step-badge">Recherche en cours</span>
          </div>

          <p class="preview-eyebrow">Votre sélection</p>
          <h2>Quel prénom préférez-vous ?</h2>

          <div class="name-card">
            <div class="name-illustration">É</div>

            <div>
              <strong>Éléonore</strong>
              <span>Origine grecque</span>
            </div>

            <span class="heart">♡</span>
          </div>

          <div class="choice-buttons">
            <span>Passer</span>
            <strong>J’aime</strong>
          </div>

          <div class="progress">
            <span></span>
          </div>

          <small>12 prénoms découverts sur 40</small>
        </article>

        <article class="preview-card match-card">
          <span class="match-icon">♥</span>

          <div>
            <small>Un prénom en commun !</small>
            <strong>Vous aimez tous les deux Éléonore</strong>
          </div>
        </article>

        <article class="preview-card participants-card">
          <small>Votre recherche</small>

          <div class="participants">
            <span>V</span>
            <span>L</span>
            <span class="participant-check">✓</span>
          </div>
        </article>
      </div>
    </section>

    <section class="features">
      <article>
        <span class="feature-number">01</span>
        <h2>Créez votre recherche</h2>
        <p>Préparez une sélection de prénoms adaptée à vos envies.</p>
      </article>

      <article>
        <span class="feature-number">02</span>
        <h2>Invitez votre partenaire</h2>
        <p>Comparez vos choix dans un espace partagé et personnel.</p>
      </article>

      <article>
        <span class="feature-number">03</span>
        <h2>Découvrez vos favoris</h2>
        <p>Retrouvez facilement les prénoms que vous aimez en commun.</p>
      </article>
    </section>

    <footer>
      <span>Le Bon Prénom</span>
      <span>Une manière simple de choisir ensemble.</span>
    </footer>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(html) {
  min-width: 320px;
  background: #fffaf8;
}

:global(body) {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  color: #29263b;
  background:
    radial-gradient(circle at 4% 8%, rgba(255, 213, 220, 0.72), transparent 31rem),
    radial-gradient(circle at 94% 52%, rgba(220, 212, 255, 0.58), transparent 34rem),
    linear-gradient(145deg, #fffaf8 0%, #f8f5ff 100%);
  font-family: Inter, Avenir, Helvetica, Arial, sans-serif;
}

:global(button) {
  font: inherit;
}

button {
  transition:
    transform 150ms ease,
    box-shadow 150ms ease,
    opacity 150ms ease;
}

button:not(:disabled):hover {
  transform: translateY(-2px);
}

button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.public-page {
  width: min(1180px, calc(100% - 40px));
  min-height: 100vh;
  margin: 0 auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 92px;
  border-bottom: 1px solid rgba(75, 63, 116, 0.12);
}

.brand {
  display: flex;
  align-items: center;
  gap: 13px;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  color: white;
  border-radius: 15px;
  background: #5e51a4;
  box-shadow: 0 10px 25px rgba(94, 81, 164, 0.23);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 17px;
}

.brand small {
  margin-top: 2px;
  color: #77738d;
  font-size: 12px;
}

.header-login-button {
  padding: 10px 17px;
  color: #514977;
  border: 1px solid rgba(81, 73, 119, 0.2);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.68);
  cursor: pointer;
  font-weight: 800;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.02fr) minmax(420px, 0.98fr);
  align-items: center;
  gap: 70px;
  min-height: 690px;
  padding: 70px 0;
}

.eyebrow,
.preview-eyebrow {
  margin: 0 0 13px;
  color: #7667bd;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero h1 {
  max-width: 680px;
  margin: 0;
  color: #29273d;
  font-size: clamp(47px, 6.2vw, 76px);
  line-height: 0.98;
  letter-spacing: -0.058em;
}

.hero h1 span {
  color: #7465b7;
}

.hero-description {
  max-width: 620px;
  margin: 27px 0 0;
  color: #6f6b7d;
  font-size: 18px;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 13px;
  margin-top: 34px;
}

.primary-button,
.secondary-button {
  min-height: 52px;
  padding: 0 22px;
  border-radius: 13px;
  cursor: pointer;
  font-weight: 850;
}

.primary-button {
  color: white;
  border: 0;
  background: #6555a6;
  box-shadow: 0 14px 30px rgba(101, 85, 166, 0.24);
}

.secondary-button {
  color: #5e5485;
  border: 1px solid rgba(94, 84, 133, 0.2);
  background: rgba(255, 255, 255, 0.74);
}

.error-message {
  max-width: 560px;
  margin: 18px 0 0;
  padding: 12px 14px;
  color: #a93d52;
  border-radius: 10px;
  background: #fff0f2;
  font-size: 13px;
  font-weight: 700;
}

.trust-line {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 22px;
  color: #777286;
  font-size: 12px;
  font-weight: 650;
}

.trust-icon {
  display: grid;
  width: 21px;
  height: 21px;
  place-items: center;
  color: #367557;
  border-radius: 50%;
  background: #e4f5ea;
  font-size: 11px;
  font-weight: 900;
}

.preview {
  position: relative;
  min-height: 545px;
}

.decorative-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(1px);
}

.circle-one {
  top: 35px;
  right: 10px;
  width: 360px;
  height: 360px;
  background: linear-gradient(145deg, rgba(255, 208, 218, 0.74), rgba(222, 214, 255, 0.67));
}

.circle-two {
  bottom: 30px;
  left: 0;
  width: 230px;
  height: 230px;
  background: rgba(255, 236, 214, 0.76);
}

.preview-card {
  position: absolute;
  border: 1px solid rgba(88, 76, 141, 0.12);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 28px 70px rgba(72, 61, 111, 0.16);
  backdrop-filter: blur(18px);
}

.main-card {
  top: 25px;
  right: 16px;
  z-index: 2;
  width: min(430px, calc(100% - 35px));
  padding: 27px;
  border-radius: 28px;
  transform: rotate(1.5deg);
}

.card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 33px;
}

.preview-logo {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: white;
  border-radius: 13px;
  background: #6555a6;
  font-size: 10px;
  font-weight: 900;
}

.step-badge {
  padding: 7px 10px;
  color: #665a9a;
  border-radius: 9px;
  background: #f0edfb;
  font-size: 10px;
  font-weight: 800;
}

.main-card h2 {
  margin: 0 0 22px;
  color: #353145;
  font-size: 23px;
}

.name-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 17px;
  border: 1px solid #ece8f3;
  border-radius: 18px;
  background: #fdfcff;
}

.name-illustration {
  display: grid;
  width: 57px;
  height: 57px;
  flex: 0 0 auto;
  place-items: center;
  color: #514388;
  border-radius: 17px;
  background: linear-gradient(145deg, #ffe0e5, #ded7ff);
  font-size: 24px;
  font-weight: 900;
}

.name-card > div:nth-child(2) {
  flex: 1;
}

.name-card strong,
.name-card span {
  display: block;
}

.name-card strong {
  color: #3b374b;
  font-size: 18px;
}

.name-card span {
  margin-top: 4px;
  color: #8a8497;
  font-size: 11px;
}

.name-card .heart {
  color: #cf7187;
  font-size: 26px;
}

.choice-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 11px;
  margin-top: 16px;
}

.choice-buttons span,
.choice-buttons strong {
  display: grid;
  min-height: 45px;
  place-items: center;
  border-radius: 12px;
  font-size: 12px;
}

.choice-buttons span {
  color: #777286;
  background: #f3f1f6;
}

.choice-buttons strong {
  color: white;
  background: #cf7187;
}

.progress {
  height: 6px;
  margin-top: 25px;
  overflow: hidden;
  border-radius: 999px;
  background: #eeebf3;
}

.progress span {
  display: block;
  width: 38%;
  height: 100%;
  border-radius: inherit;
  background: #7465b7;
}

.main-card > small {
  display: block;
  margin-top: 9px;
  color: #9791a2;
  font-size: 10px;
  text-align: right;
}

.match-card {
  right: 0;
  bottom: 12px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 13px;
  width: 300px;
  padding: 16px;
  border-radius: 17px;
  transform: rotate(-2deg);
}

.match-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  color: white;
  border-radius: 13px;
  background: #cf7187;
}

.match-card small,
.match-card strong {
  display: block;
}

.match-card small {
  margin-bottom: 4px;
  color: #a26776;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
}

.match-card strong {
  color: #4b3940;
  font-size: 12px;
  line-height: 1.35;
}

.participants-card {
  bottom: 72px;
  left: 7px;
  z-index: 3;
  padding: 15px 17px;
  border-radius: 16px;
  transform: rotate(-3deg);
}

.participants-card small {
  color: #898397;
  font-size: 10px;
  font-weight: 750;
}

.participants {
  display: flex;
  margin-top: 9px;
}

.participants span {
  display: grid;
  width: 33px;
  height: 33px;
  margin-left: -5px;
  place-items: center;
  color: white;
  border: 3px solid white;
  border-radius: 50%;
  background: #7465b7;
  font-size: 10px;
  font-weight: 900;
}

.participants span:first-child {
  margin-left: 0;
  background: #cf7187;
}

.participants .participant-check {
  color: #347454;
  background: #def2e5;
}

.features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  padding: 10px 0 70px;
}

.features article {
  padding: 27px;
  border: 1px solid rgba(88, 76, 141, 0.11);
  border-radius: 21px;
  background: rgba(255, 255, 255, 0.63);
}

.feature-number {
  color: #cf7187;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.features h2 {
  margin: 16px 0 8px;
  font-size: 17px;
}

.features p {
  margin: 0;
  color: #777286;
  font-size: 13px;
  line-height: 1.6;
}

footer {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 25px 0 35px;
  color: #9892a5;
  border-top: 1px solid rgba(75, 63, 116, 0.1);
  font-size: 12px;
}

footer span:first-child {
  color: #5d5577;
  font-weight: 850;
}

@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 20px;
    padding-top: 60px;
  }

  .hero-content {
    max-width: 760px;
  }

  .preview {
    width: min(560px, 100%);
    margin: 10px auto 0;
  }
}

@media (max-width: 680px) {
  .public-page {
    width: min(100% - 24px, 1180px);
  }

  .topbar {
    min-height: 76px;
  }

  .brand small {
    display: none;
  }

  .hero {
    min-height: auto;
    padding: 48px 0;
  }

  .hero h1 {
    font-size: 45px;
  }

  .hero-description {
    font-size: 16px;
  }

  .hero-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button,
  .secondary-button {
    width: 100%;
  }

  .preview {
    min-height: 510px;
  }

  .main-card {
    right: 0;
    width: 100%;
    padding: 21px;
  }

  .participants-card {
    left: 0;
  }

  .match-card {
    right: 0;
    width: min(290px, 88%);
  }

  .features {
    grid-template-columns: 1fr;
  }

  footer {
    flex-direction: column;
  }
}

@media (max-width: 430px) {
  .header-login-button {
    padding: 9px 11px;
    font-size: 12px;
  }

  .hero h1 {
    font-size: 39px;
  }

  .preview {
    min-height: 500px;
  }

  .participants-card {
    display: none;
  }
}
</style>
