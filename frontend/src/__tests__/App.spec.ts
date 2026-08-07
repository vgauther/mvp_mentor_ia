import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../App.vue";

const { logoutMock, updateTokenMock } = vi.hoisted(() => ({
  logoutMock: vi.fn<(options: { redirectUri: string }) => Promise<void>>(),
  updateTokenMock: vi.fn<(minValidity: number) => Promise<boolean>>(),
}));

logoutMock.mockResolvedValue(undefined);
updateTokenMock.mockResolvedValue(false);

vi.mock("../auth/keycloak", () => ({
  default: {
    token: "jeton-test",
    updateToken: updateTokenMock,
    logout: logoutMock,
  },
}));

const profile = {
  id: 12,
  username: "utilisateur",
  email: "utilisateur@example.com",
  display_name: "Victor",
  roles: ["parent", "user"],
  created_at: "2026-07-30T08:30:00Z",
  updated_at: "2026-07-30T08:30:00Z",
};

const activeSearch = {
  id: 41,
  title: "Notre futur prénom",
  genders: ["female", "male", "mixed"],
  origins: [],
  min_length: null,
  max_length: null,
  first_letters: [],
  status: "active",
  status_label: "Active",
  creator: {
    id: profile.id,
    username: profile.username,
    display_name: profile.display_name,
  },
  participants: [
    {
      id: 91,
      profile: {
        id: profile.id,
        username: profile.username,
        display_name: profile.display_name,
      },
      role: "owner",
      role_label: "Propriétaire",
      invitation_status: "accepted",
      invitation_status_label: "Acceptée",
      created_at: "2026-08-04T08:00:00Z",
      updated_at: "2026-08-04T08:00:00Z",
    },
  ],
  created_at: "2026-08-04T08:00:00Z",
  updated_at: "2026-08-04T08:00:00Z",
};

const firstNameOrigins = [
  {
    id: "latine",
    label: "Latine",
    description: "Origine latine.",
  },
];

const proposedFirstName = {
  id: 301,
  name: "Lina",
  gender: "female",
  gender_label: "Féminin",
  origin: "latine",
  origin_label: "Latine",
  meaning: "Douce",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

async function finishInitialLoading() {
  await flushPromises();
  await flushPromises();
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.clearAllMocks();

  logoutMock.mockResolvedValue(undefined);
  updateTokenMock.mockResolvedValue(false);
});

describe("App", () => {
  it("envoie le jeton Keycloak et affiche le profil ainsi que les recherches Django", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([activeSearch]));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(App);

    expect(wrapper.text()).toContain("Vérification de votre identité");

    await finishInitialLoading();

    expect(fetchMock).toHaveBeenCalledTimes(2);

    const profileCall = fetchMock.mock.calls[0];
    const searchesCall = fetchMock.mock.calls[1];

    if (!profileCall || !searchesCall) {
      throw new Error(
        "Les appels initiaux vers Django n'ont pas été effectués.",
      );
    }

    const [profileUrl, profileOptions] = profileCall;
    const profileHeaders = new Headers(profileOptions?.headers);

    expect(profileUrl).toBe("http://127.0.0.1:8000/api/me/");
    expect(profileHeaders.get("Authorization")).toBe("Bearer jeton-test");

    const [searchesUrl, searchesOptions] = searchesCall;
    const searchesHeaders = new Headers(searchesOptions?.headers);

    expect(searchesUrl).toBe("http://127.0.0.1:8000/api/searches/");
    expect(searchesHeaders.get("Authorization")).toBe("Bearer jeton-test");

    expect(wrapper.text()).toContain("Bonjour Victor");
    expect(wrapper.text()).toContain("Tes recherches de prénoms");
    expect(wrapper.text()).toContain("Notre futur prénom");
    expect(wrapper.text()).toContain("Ma recherche");
  });

  it("affiche un état vide lorsque le compte ne possède aucune recherche", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([]));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(App);

    await finishInitialLoading();

    expect(wrapper.text()).toContain("Ta première recherche commence ici");
    expect(wrapper.text()).toContain("Créer ma première recherche");
  });

  it("ouvre le parcours, permet d’afficher les détails et revient aux recherches", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([activeSearch]))
      .mockResolvedValueOnce(jsonResponse(proposedFirstName))
      .mockResolvedValueOnce(jsonResponse(proposedFirstName))
      .mockResolvedValueOnce(jsonResponse([activeSearch]));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);

    const wrapper = mount(App);

    await finishInitialLoading();
    await wrapper.get('[data-test="open-search-button"]').trigger("click");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      "http://127.0.0.1:8000/api/searches/41/next-first-name/",
    );
    expect(wrapper.text()).toContain("Lina");
    expect(wrapper.text()).toContain("Je n’aime pas");
    expect(wrapper.text()).toContain("J’aime");
    expect(wrapper.find('[data-test="browse-first-names"]').exists()).toBe(
      false,
    );

    await wrapper
      .get('[data-test="open-current-search-details"]')
      .trigger("click");

    expect(wrapper.text()).toContain("Détail de ta recherche");
    expect(wrapper.find('[data-test="browse-first-names"]').exists()).toBe(
      true,
    );
    expect(fetchMock).toHaveBeenCalledTimes(3);

    await wrapper.get('[data-test="browse-first-names"]').trigger("click");
    await flushPromises();

    await wrapper.get('[data-test="back-to-searches"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Tes recherches de prénoms");
    expect(wrapper.text()).toContain("Notre futur prénom");
    expect(wrapper.find('[data-test="back-to-searches"]').exists()).toBe(
      false,
    );

    await wrapper
      .get('[data-test="open-search-details-button"]')
      .trigger("click");

    expect(wrapper.text()).toContain("Détail de ta recherche");
    expect(wrapper.find('[data-test="browse-first-names"]').exists()).toBe(
      true,
    );
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it("ouvre le détail lorsqu’une recherche terminée est sélectionnée", async () => {
    const completedSearch = {
      ...activeSearch,
      status: "completed",
      status_label: "Terminée",
    };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([completedSearch]));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);

    const wrapper = mount(App);

    await finishInitialLoading();
    await wrapper
      .get('[data-test="open-search-details-button"]')
      .trigger("click");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("La recherche est terminée.");
    expect(
      wrapper.get('[data-test="browse-first-names"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("crée une recherche avec son titre et les filtres sélectionnés", async () => {
    const createdSearch = {
      ...activeSearch,
      id: 42,
      title: "Prénoms pour bébé",
    };

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(firstNameOrigins))
      .mockResolvedValueOnce(jsonResponse(createdSearch, 201));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(App);

    await finishInitialLoading();

    await wrapper.get('[data-test="create-search-button"]').trigger("click");
    await flushPromises();
    await wrapper
      .get('[data-test="search-title-input"]')
      .setValue("Prénoms pour bébé");
    await wrapper
      .get('[data-test="create-search-origin-latine"]')
      .trigger("click");
    await wrapper.get('[data-test="create-search-min-length"]').setValue("4");
    await wrapper.get('[data-test="create-search-max-length"]').setValue("8");
    await wrapper
      .get('[data-test="create-search-first-letter-A"]')
      .trigger("click");
    await wrapper.get('[data-test="create-search-form"]').trigger("submit");

    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(4);

    const createCall = fetchMock.mock.calls[3];

    if (!createCall) {
      throw new Error("L'appel de création vers Django n'a pas été effectué.");
    }

    const [url, options] = createCall;
    const headers = new Headers(options?.headers);

    expect(url).toBe("http://127.0.0.1:8000/api/searches/");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(
      JSON.stringify({
        title: "Prénoms pour bébé",
        genders: ["female", "male", "mixed"],
        origins: ["latine"],
        min_length: 4,
        max_length: 8,
        first_letters: ["A"],
      }),
    );
    expect(headers.get("Authorization")).toBe("Bearer jeton-test");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(wrapper.text()).toContain(
      "La recherche « Prénoms pour bébé » a bien été créée.",
    );
    expect(wrapper.text()).toContain("Prénoms pour bébé");
  });

  it("refuse localement une création sans titre", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(firstNameOrigins));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(App);

    await finishInitialLoading();

    await wrapper.get('[data-test="create-search-button"]').trigger("click");
    await wrapper.get('[data-test="create-search-form"]').trigger("submit");

    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(wrapper.get('[role="alert"]').text()).toBe(
      "Donne un nom à cette recherche.",
    );
  });

  it("modifie le nom d’affichage avec PATCH depuis le profil", async () => {
    const updatedProfile = {
      ...profile,
      display_name: "Nouveau nom",
    };

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(updatedProfile));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(App);

    await finishInitialLoading();
    await wrapper.get('[data-test="profile-navigation"]').trigger("click");
    await wrapper
      .get('[data-test="display-name-input"]')
      .setValue("Nouveau nom");
    await wrapper.get('[data-test="profile-form"]').trigger("submit");

    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(3);

    const patchCall = fetchMock.mock.calls[2];

    if (!patchCall) {
      throw new Error("L'appel PATCH vers Django n'a pas été effectué.");
    }

    const [url, options] = patchCall;
    const headers = new Headers(options?.headers);

    expect(url).toBe("http://127.0.0.1:8000/api/me/");
    expect(options?.method).toBe("PATCH");
    expect(options?.body).toBe(
      JSON.stringify({
        display_name: "Nouveau nom",
      }),
    );
    expect(headers.get("Authorization")).toBe("Bearer jeton-test");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(wrapper.text()).toContain(
      "Votre nom d’affichage a bien été enregistré.",
    );
    expect(wrapper.text()).toContain("Bonjour Nouveau nom");
  });

  it("recherche un utilisateur avec son e-mail exact depuis le profil", async () => {
    const foundProfile = {
      id: 25,
      username: "autre-utilisateur",
      email: "autre@example.com",
      display_name: "Autre personne",
    };

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(profile))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(foundProfile));

    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(App);

    await finishInitialLoading();
    await wrapper.get('[data-test="profile-navigation"]').trigger("click");
    await wrapper
      .get('[data-test="lookup-email-input"]')
      .setValue("autre@example.com");
    await wrapper.get('[data-test="lookup-form"]').trigger("submit");

    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(3);

    const lookupCall = fetchMock.mock.calls[2];

    if (!lookupCall) {
      throw new Error("L'appel de recherche vers Django n'a pas été effectué.");
    }

    const [url, options] = lookupCall;
    const headers = new Headers(options?.headers);

    expect(url).toBe(
      "http://127.0.0.1:8000/api/profiles/lookup/" +
        "?email=autre%40example.com",
    );
    expect(headers.get("Authorization")).toBe("Bearer jeton-test");

    const result = wrapper.get('[data-test="lookup-result"]');

    expect(result.text()).toContain("Utilisateur trouvé");
    expect(result.text()).toContain("Autre personne");
    expect(result.text()).toContain("autre@example.com");
    expect(result.text()).toContain("@autre-utilisateur");
  });

  it("affiche une erreur lorsque Django refuse la connexion", async () => {
    vi.stubEnv("VITE_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(null, { status: 401 })),
    );

    const wrapper = mount(App);

    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe(
      "Impossible de vérifier votre identité auprès de Django.",
    );
  });
});
