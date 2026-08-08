<script setup lang="ts">
import { ref } from 'vue'

import logoIconUrl from './assets/brand/logo-icon.png'
import keycloak from './auth/keycloak'
import FeatherIcon from './components/FeatherIcon.vue'

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
        <img :src="logoIconUrl" alt="" />

        <span>
          <strong>Le Bon Prénom</strong>
          <small>Trouvez-le ensemble</small>
        </span>
      </a>

      <nav aria-label="Navigation principale">
        <a href="#fonctionnement">Comment ça marche ?</a>

        <button
          type="button"
          class="header-login-button"
          :disabled="redirectingTo !== null"
          @click="login"
        >
          <FeatherIcon name="user" :size="16" />
          Se connecter
        </button>
      </nav>
    </header>

    <section class="hero">
      <div class="hero-content">
        <p class="eyebrow">
          <span><FeatherIcon name="heart" :size="14" /></span>
          Le choix qui vous rapproche
        </p>

        <h1>
          Le bon prénom,<br />
          c’est celui que vous aimez
          <span>ensemble.</span>
        </h1>

        <p class="hero-description">
          Explorez les prénoms chacun de votre côté et découvrez simplement ceux qui font
          battre vos deux cœurs.
        </p>

        <div class="hero-actions">
          <button
            type="button"
            class="primary-button"
            :disabled="redirectingTo !== null"
            @click="register"
          >
            {{ redirectingTo === 'register' ? 'Ouverture du formulaire…' : 'Commencer à deux' }}
            <FeatherIcon v-if="redirectingTo !== 'register'" name="arrow-right" :size="18" />
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
          <FeatherIcon name="alert-circle" :size="17" />
          {{ errorMessage }}
        </p>

        <p class="trust-line">
          <FeatherIcon name="shield" :size="15" />
          Espace personnel et connexion sécurisée
        </p>
      </div>

      <div class="preview" aria-hidden="true">
        <span class="decorative-shape shape-blue"></span>
        <span class="decorative-shape shape-orange"></span>
        <span class="decorative-dot dot-one"></span>
        <span class="decorative-dot dot-two"></span>

        <article class="preview-card main-card">
          <div class="preview-header">
            <span class="preview-brand">
              <img :src="logoIconUrl" alt="" />
              <strong>Le Bon Prénom</strong>
            </span>

            <span class="step-badge">Recherche en cours</span>
          </div>

          <div class="preview-title">
            <p>À vous de choisir</p>
            <h2>Est-ce que ce prénom vous plaît ?</h2>
          </div>

          <div class="name-card">
            <span class="name-initial">É</span>

            <div>
              <strong>Éléonore</strong>
              <span>Origine grecque · Éclat du soleil</span>
            </div>
          </div>

          <div class="choice-buttons">
            <span><FeatherIcon name="x" :size="18" />Je n’aime pas</span>
            <strong><FeatherIcon name="heart" :size="18" />J’aime</strong>
          </div>
        </article>

        <article class="preview-card match-card">
          <span class="match-icon"><FeatherIcon name="heart" :size="21" /></span>

          <div>
            <small>C’est un match !</small>
            <strong>Éléonore vous plaît à tous les deux</strong>
          </div>
        </article>

        <article class="preview-card duo-card">
          <span class="avatars"><i>V</i><i>L</i></span>

          <span>
            <small>Votre recherche</small>
            <strong>2 participants</strong>
          </span>

          <FeatherIcon name="check-circle" :size="19" />
        </article>
      </div>
    </section>

    <section id="fonctionnement" class="how-it-works">
      <div class="section-heading">
        <p>Simple comme un coup de cœur</p>
        <h2>Trois étapes, un choix à deux.</h2>
      </div>

      <div class="steps">
        <article>
          <span class="step-icon icon-orange"><FeatherIcon name="search" :size="24" /></span>
          <span class="step-number">01</span>
          <h3>Créez votre recherche</h3>
          <p>Choisissez vos préférences pour découvrir des prénoms qui vous correspondent.</p>
        </article>

        <article>
          <span class="step-icon icon-blue"><FeatherIcon name="user-plus" :size="24" /></span>
          <span class="step-number">02</span>
          <h3>Invitez votre partenaire</h3>
          <p>Chacun avance librement dans la même sélection, à son propre rythme.</p>
        </article>

        <article>
          <span class="step-icon icon-yellow"><FeatherIcon name="heart" :size="24" /></span>
          <span class="step-number">03</span>
          <h3>Découvrez vos matchs</h3>
          <p>Les prénoms aimés à deux apparaissent naturellement dans vos résultats.</p>
        </article>
      </div>
    </section>

    <section class="shared-choice">
      <div class="shared-visual" aria-hidden="true">
        <span class="shared-heart"><FeatherIcon name="heart" :size="46" /></span>
        <span class="person person-one">V</span>
        <span class="connection"></span>
        <span class="person person-two">L</span>
      </div>

      <div>
        <p class="section-kicker">Pensé pour choisir sereinement</p>
        <h2>Chacun donne son avis.<br />Vos matchs créent votre liste commune.</h2>
        <p>
          Pas besoin de se convaincre à chaque prénom. Vous choisissez chacun à votre rythme,
          puis l’application fait ressortir naturellement ce que vous aimez en commun.
        </p>

        <ul>
          <li><FeatherIcon name="check" :size="17" />Des choix simples et rapides</li>
          <li><FeatherIcon name="check" :size="17" />Des préférences partagées sans pression</li>
          <li><FeatherIcon name="check" :size="17" />Une liste commune toujours accessible</li>
        </ul>
      </div>
    </section>

    <section class="final-cta">
      <span class="cta-decoration decoration-left"></span>
      <span class="cta-decoration decoration-right"></span>

      <div>
        <p>Votre futur coup de cœur vous attend</p>
        <h2>Prêts à trouver Le Bon Prénom ?</h2>

        <button type="button" :disabled="redirectingTo !== null" @click="register">
          {{ redirectingTo === 'register' ? 'Ouverture du formulaire…' : 'Créer notre espace' }}
          <FeatherIcon v-if="redirectingTo !== 'register'" name="arrow-right" :size="18" />
        </button>
      </div>
    </section>

    <footer>
      <a class="brand footer-brand" href="/" aria-label="Accueil Le Bon Prénom">
        <img :src="logoIconUrl" alt="" />
        <span><strong>Le Bon Prénom</strong><small>Trouvez-le ensemble</small></span>
      </a>

      <span>Une manière simple et douce de choisir à deux.</span>
    </footer>
  </main>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(html) {
  min-width: 320px;
  scroll-behavior: smooth;
  background: #fbfaf8;
}

:global(body) {
  min-width: 320px;
  min-height: 100vh;
  margin: 0;
  color: #3f2e20;
  background: #fbfaf8;
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
  opacity: 0.68;
}

.public-page {
  overflow: hidden;
}

.topbar,
.hero,
.how-it-works,
.shared-choice,
footer {
  width: min(1180px, calc(100% - 40px));
  margin-inline: auto;
}

.topbar {
  display: flex;
  min-height: 88px;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(126, 83, 35, 0.1);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.brand img {
  width: 47px;
  height: 47px;
  border-radius: 14px;
  object-fit: cover;
  box-shadow: 0 9px 22px rgba(238, 137, 27, 0.15);
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  color: #d87208;
  font-size: 17px;
  line-height: 1.1;
}

.brand small {
  margin-top: 3px;
  color: #9a806b;
  font-size: 11px;
  font-weight: 700;
}

nav {
  display: flex;
  align-items: center;
  gap: 25px;
}

nav > a {
  color: #776353;
  font-size: 13px;
  font-weight: 800;
  text-decoration: none;
}

nav > a:hover {
  color: #d87208;
}

.header-login-button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  color: #74430c;
  border: 1px solid #eed9c2;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 850;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.04fr) minmax(430px, 0.96fr);
  align-items: center;
  gap: 70px;
  min-height: 690px;
  padding: 72px 0 82px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin: 0 0 22px;
  color: #8d500c;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow > span {
  display: grid;
  width: 29px;
  height: 29px;
  place-items: center;
  color: #9a5200;
  border-radius: 9px;
  background: #fee4b8;
}

.hero h1 {
  max-width: 680px;
  margin: 0;
  color: #38291d;
  font-size: clamp(46px, 5.6vw, 72px);
  line-height: 1.02;
  letter-spacing: -0.055em;
}

.hero h1 span {
  position: relative;
  z-index: 0;
  display: inline-block;
  color: #df7808;
}

.hero h1 span::after {
  position: absolute;
  right: -8px;
  bottom: 3px;
  left: -5px;
  z-index: -1;
  height: 13px;
  border-radius: 999px;
  background: #fee4b8;
  content: '';
  transform: rotate(-1deg);
}

.hero-description {
  max-width: 590px;
  margin: 27px 0 0;
  color: #806c5c;
  font-size: 18px;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 33px;
}

.primary-button,
.secondary-button {
  display: inline-flex;
  min-height: 53px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 22px;
  border-radius: 13px;
  cursor: pointer;
  font-weight: 850;
}

.primary-button {
  color: #fff;
  border: 0;
  background: #f28a19;
  box-shadow: 0 14px 28px rgba(228, 121, 5, 0.23);
}

.primary-button:hover {
  background: #e47a08;
  box-shadow: 0 17px 32px rgba(228, 121, 5, 0.28);
}

.secondary-button {
  color: #74430c;
  border: 1px solid #ead9c8;
  background: #fff;
}

.error-message {
  display: flex;
  max-width: 560px;
  align-items: center;
  gap: 8px;
  margin: 18px 0 0;
  padding: 12px 14px;
  color: #a84444;
  border-radius: 11px;
  background: #fff0ec;
  font-size: 13px;
  font-weight: 750;
}

.trust-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 21px 0 0;
  color: #897568;
  font-size: 12px;
  font-weight: 700;
}

.trust-line :deep(svg) {
  color: #3e806d;
}

.preview {
  position: relative;
  min-height: 550px;
}

.decorative-shape,
.decorative-dot {
  position: absolute;
  display: block;
  pointer-events: none;
}

.decorative-shape {
  border-radius: 50%;
}

.shape-blue {
  top: 8px;
  right: -12px;
  width: 390px;
  height: 390px;
  background: #a3dff1;
  opacity: 0.7;
}

.shape-orange {
  bottom: 28px;
  left: 5px;
  width: 245px;
  height: 245px;
  background: #fee4b8;
}

.decorative-dot {
  width: 13px;
  height: 13px;
  border-radius: 4px;
  background: #ffa43a;
  transform: rotate(24deg);
}

.dot-one {
  top: 2px;
  left: 50px;
}

.dot-two {
  right: 15px;
  bottom: 80px;
  width: 9px;
  height: 9px;
  background: #3f2e20;
}

.preview-card {
  position: absolute;
  border: 1px solid rgba(126, 83, 35, 0.11);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 26px 58px rgba(92, 57, 23, 0.14);
  backdrop-filter: blur(16px);
}

.main-card {
  top: 37px;
  right: 10px;
  z-index: 2;
  width: min(445px, calc(100% - 32px));
  padding: 25px;
  border-radius: 27px;
  transform: rotate(1.2deg);
}

.preview-header,
.preview-brand {
  display: flex;
  align-items: center;
}

.preview-header {
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f1e3d5;
}

.preview-brand {
  gap: 8px;
}

.preview-brand img {
  width: 31px;
  height: 31px;
  border-radius: 9px;
}

.preview-brand strong {
  color: #d87208;
  font-size: 11px;
}

.step-badge {
  padding: 7px 10px;
  color: #396977;
  border-radius: 9px;
  background: #dff4fa;
  font-size: 9px;
  font-weight: 850;
}

.preview-title {
  padding: 23px 0 18px;
  text-align: center;
}

.preview-title p {
  margin: 0 0 6px;
  color: #d87208;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.preview-title h2 {
  margin: 0;
  color: #473426;
  font-size: 21px;
}

.name-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 19px;
  border: 1px solid #f0dfce;
  border-radius: 18px;
  background: #fffaf2;
}

.name-initial {
  display: grid;
  width: 58px;
  height: 58px;
  flex: 0 0 auto;
  place-items: center;
  color: #77450d;
  border-radius: 17px;
  background: linear-gradient(145deg, #fee4b8, #ffc065);
  font-size: 25px;
  font-weight: 900;
}

.name-card strong,
.name-card div span {
  display: block;
}

.name-card strong {
  color: #473426;
  font-size: 20px;
}

.name-card div span {
  margin-top: 5px;
  color: #947f6e;
  font-size: 10px;
}

.choice-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 15px;
}

.choice-buttons > span,
.choice-buttons > strong {
  display: flex;
  min-height: 47px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border-radius: 12px;
  font-size: 11px;
}

.choice-buttons > span {
  color: #786555;
  background: #f3efeb;
}

.choice-buttons > strong {
  color: #fff;
  background: #f28a19;
}

.match-card {
  right: -5px;
  bottom: 19px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 13px;
  width: 305px;
  padding: 16px;
  border-radius: 17px;
  transform: rotate(-2deg);
}

.match-icon {
  display: grid;
  width: 43px;
  height: 43px;
  flex: 0 0 auto;
  place-items: center;
  color: #fff;
  border-radius: 13px;
  background: #ffa43a;
}

.match-card small,
.match-card strong,
.duo-card small,
.duo-card strong {
  display: block;
}

.match-card small {
  margin-bottom: 4px;
  color: #d87208;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.match-card strong {
  color: #4d3929;
  font-size: 12px;
  line-height: 1.35;
}

.duo-card {
  bottom: 88px;
  left: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 13px 15px;
  color: #4a7580;
  border-radius: 16px;
  transform: rotate(-2.5deg);
}

.avatars {
  display: flex;
}

.avatars i {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  color: #74430c;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #ffc065;
  font-size: 9px;
  font-style: normal;
  font-weight: 900;
}

.avatars i + i {
  margin-left: -9px;
  color: #2d6877;
  background: #a3dff1;
}

.duo-card small {
  color: #9a806b;
  font-size: 8px;
}

.duo-card strong {
  margin-top: 2px;
  color: #4d3929;
  font-size: 10px;
}

.how-it-works {
  padding: 88px 0 94px;
}

.section-heading {
  max-width: 690px;
  margin: 0 auto 45px;
  text-align: center;
}

.section-heading p,
.section-kicker,
.final-cta p {
  margin: 0 0 12px;
  color: #d87208;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.section-heading h2,
.shared-choice h2,
.final-cta h2 {
  margin: 0;
  color: #3d2c1f;
  font-size: clamp(33px, 4.2vw, 49px);
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.steps article {
  position: relative;
  min-height: 270px;
  padding: 27px;
  border: 1px solid #ecdfd3;
  border-radius: 22px;
  background: #fff;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease;
}

.steps article:hover {
  box-shadow: 0 18px 40px rgba(103, 65, 30, 0.09);
  transform: translateY(-4px);
}

.step-icon {
  display: grid;
  width: 53px;
  height: 53px;
  place-items: center;
  color: #75440d;
  border-radius: 16px;
}

.icon-orange {
  background: #ffc065;
}

.icon-blue {
  color: #2d6877;
  background: #a3dff1;
}

.icon-yellow {
  background: #fee4b8;
}

.step-number {
  position: absolute;
  top: 27px;
  right: 27px;
  color: #d7c6b7;
  font-size: 12px;
  font-weight: 900;
}

.steps h3 {
  margin: 28px 0 10px;
  color: #463326;
  font-size: 19px;
}

.steps p {
  margin: 0;
  color: #887568;
  font-size: 13px;
  line-height: 1.65;
}

.shared-choice {
  display: grid;
  grid-template-columns: minmax(350px, 0.88fr) minmax(0, 1.12fr);
  align-items: center;
  gap: 80px;
  padding: 105px 0;
}

.shared-visual {
  position: relative;
  min-height: 385px;
  border-radius: 40px;
  background: #a3dff1;
  overflow: hidden;
}

.shared-visual::before,
.shared-visual::after {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.32);
  content: '';
}

.shared-visual::before {
  top: -65px;
  left: -30px;
  width: 210px;
  height: 210px;
}

.shared-visual::after {
  right: -45px;
  bottom: -75px;
  width: 250px;
  height: 250px;
}

.person,
.shared-heart {
  position: absolute;
  z-index: 2;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-weight: 900;
}

.person {
  top: 50%;
  width: 88px;
  height: 88px;
  color: #70400b;
  border: 7px solid rgba(255, 255, 255, 0.8);
  background: #ffc065;
  transform: translateY(-50%);
}

.person-one {
  left: 13%;
}

.person-two {
  right: 13%;
  color: #2a6471;
  background: #fff;
}

.connection {
  position: absolute;
  top: 50%;
  right: 23%;
  left: 23%;
  height: 4px;
  background: rgba(255, 255, 255, 0.75);
  transform: translateY(-50%);
}

.shared-heart {
  top: 50%;
  left: 50%;
  width: 100px;
  height: 100px;
  color: #fff;
  background: #ffa43a;
  box-shadow: 0 18px 35px rgba(163, 86, 6, 0.22);
  transform: translate(-50%, -50%);
}

.shared-choice > div:last-child > p:not(.section-kicker) {
  max-width: 620px;
  margin: 23px 0 0;
  color: #826f60;
  font-size: 16px;
  line-height: 1.7;
}

.shared-choice ul {
  display: grid;
  gap: 12px;
  margin: 25px 0 0;
  padding: 0;
  list-style: none;
}

.shared-choice li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #5d4939;
  font-size: 13px;
  font-weight: 800;
}

.shared-choice li :deep(svg) {
  color: #377281;
}

.final-cta {
  position: relative;
  width: min(1180px, calc(100% - 40px));
  margin: 15px auto 82px;
  padding: 73px 40px;
  overflow: hidden;
  border-radius: 32px;
  background: #fee4b8;
  text-align: center;
}

.final-cta > div {
  position: relative;
  z-index: 2;
}

.final-cta p {
  color: #9a5200;
}

.final-cta h2 {
  font-size: clamp(32px, 4.6vw, 51px);
}

.final-cta button {
  display: inline-flex;
  min-height: 53px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  margin-top: 27px;
  padding: 0 23px;
  color: #fff;
  border: 0;
  border-radius: 13px;
  background: #f28a19;
  box-shadow: 0 14px 28px rgba(190, 96, 0, 0.2);
  cursor: pointer;
  font-weight: 850;
}

.cta-decoration {
  position: absolute;
  display: block;
  border-radius: 50%;
}

.decoration-left {
  top: -90px;
  left: -80px;
  width: 250px;
  height: 250px;
  background: #ffc065;
}

.decoration-right {
  right: -60px;
  bottom: -100px;
  width: 260px;
  height: 260px;
  background: rgba(163, 223, 241, 0.62);
}

footer {
  display: flex;
  min-height: 100px;
  align-items: center;
  justify-content: space-between;
  gap: 25px;
  color: #9a8675;
  border-top: 1px solid #eadfd5;
  font-size: 12px;
}

.footer-brand img {
  width: 39px;
  height: 39px;
  border-radius: 11px;
}

.footer-brand strong {
  font-size: 14px;
}

.footer-brand small {
  font-size: 9px;
}

@media (max-width: 980px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 30px;
    padding-top: 62px;
  }

  .hero-content {
    max-width: 760px;
  }

  .preview {
    width: min(570px, 100%);
    margin-inline: auto;
  }

  .shared-choice {
    grid-template-columns: 1fr;
    gap: 50px;
  }

  .shared-visual {
    width: min(560px, 100%);
    margin-inline: auto;
  }
}

@media (max-width: 700px) {
  .topbar,
  .hero,
  .how-it-works,
  .shared-choice,
  footer,
  .final-cta {
    width: min(100% - 28px, 1180px);
  }

  .topbar {
    min-height: 76px;
  }

  nav > a,
  .brand small {
    display: none;
  }

  nav {
    gap: 0;
  }

  .brand img {
    width: 43px;
    height: 43px;
    border-radius: 12px;
  }

  .hero {
    min-height: auto;
    padding: 50px 0 62px;
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

  .steps {
    grid-template-columns: 1fr;
  }

  .steps article {
    min-height: 0;
  }

  .shared-choice {
    padding: 75px 0;
  }

  .shared-visual {
    min-height: 320px;
  }

  .final-cta {
    margin-bottom: 55px;
    padding: 60px 22px;
  }

  footer {
    align-items: flex-start;
    flex-direction: column;
    justify-content: center;
    padding: 26px 0;
  }
}

@media (max-width: 470px) {
  .brand strong {
    font-size: 15px;
  }

  .header-login-button {
    min-height: 39px;
    padding: 0 11px;
    font-size: 11px;
  }

  .header-login-button .feather-icon {
    display: none;
  }

  .hero h1 {
    font-size: 39px;
  }

  .preview {
    min-height: 520px;
  }

  .main-card {
    right: 0;
    width: 100%;
    padding: 19px;
  }

  .step-badge {
    display: none;
  }

  .match-card {
    right: 0;
    width: min(295px, 91%);
  }

  .duo-card {
    left: 0;
  }

  .shared-visual {
    min-height: 290px;
  }

  .person {
    width: 70px;
    height: 70px;
  }

  .person-one {
    left: 7%;
  }

  .person-two {
    right: 7%;
  }

  .shared-heart {
    width: 82px;
    height: 82px;
  }
}
</style>
