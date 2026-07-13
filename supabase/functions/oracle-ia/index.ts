// Edge Function Supabase — RELAIS de l'Oracle IA « payant sans clé ».
//
// Rôle : détenir NOTRE clé Anthropic (jamais exposée au navigateur), vérifier
// que l'utilisateur est connecté ET qu'il lui reste des consultations, appeler
// l'IA, puis décompter une consultation. C'est la seule façon d'offrir l'IA
// « sans clé » depuis une PWA statique (une clé embarquée serait volée).
//
// ⚠️ Ce fichier est PRÊT À DÉPLOYER mais N'A PAS ENCORE ÉTÉ testé en ligne :
// il s'active avec l'étape « Oracle payant », elle-même conditionnée à la
// publication Play Store (Play Billing pour créditer les achats). Voir
// docs/ORACLE-PAYANT.md.
//
// Secrets à poser (jamais dans le dépôt) :
//   supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
//   supabase secrets set SUPABASE_SERVICE_ROLE_KEY=...   (déjà fourni par la plateforme)
// Déploiement :  supabase functions deploy oracle-ia --no-verify-jwt
//   (on vérifie le JWT nous-mêmes pour renvoyer des erreurs lisibles)

import { createClient } from "jsr:@supabase/supabase-js@2";

// Garde-fous anti-abus : bornes strictes sur ce que le client peut demander.
const MODELES_AUTORISES = new Set(["claude-haiku-4-5-20251001"]);
const MAX_TOKENS = 1500;
const MAX_ENTREE = 12000; // caractères cumulés des messages

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const json = (o: unknown, status = 200) =>
  new Response(JSON.stringify(o), {
    status,
    headers: { ...cors, "content-type": "application/json" },
  });

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ erreur: "Méthode non autorisée" }, 405);

  // 1. Authentifier l'utilisateur via son jeton Supabase (login Google déjà en place)
  const jwt = req.headers.get("Authorization")?.replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ erreur: "Connexion requise" }, 401);

  const url = Deno.env.get("SUPABASE_URL")!;
  const service = createClient(url, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  const { data: userData, error: userErr } = await service.auth.getUser(jwt);
  if (userErr || !userData?.user) return json({ erreur: "Session invalide" }, 401);
  const userId = userData.user.id;

  // 2. Vérifier le solde de consultations (table oracle_credits, cf. schema.sql)
  const { data: credit } = await service
    .from("oracle_credits")
    .select("credits")
    .eq("user_id", userId)
    .maybeSingle();
  const solde = credit?.credits ?? 0;
  if (solde <= 0) return json({ erreur: "Plus de consultations", solde: 0 }, 402);

  // 3. Valider la requête du client (bornes strictes)
  let corps: any;
  try {
    corps = await req.json();
  } catch {
    return json({ erreur: "Requête illisible" }, 400);
  }
  const modele = String(corps?.model || "");
  if (!MODELES_AUTORISES.has(modele)) return json({ erreur: "Modèle non autorisé" }, 400);
  const messages = Array.isArray(corps?.messages) ? corps.messages : null;
  if (!messages) return json({ erreur: "messages manquants" }, 400);
  const taille = JSON.stringify(messages).length + String(corps?.system || "").length;
  if (taille > MAX_ENTREE) return json({ erreur: "Requête trop longue" }, 413);

  // 4. Appeler Anthropic avec NOTRE clé (les paramètres sensibles sont imposés ici)
  let reponse: Response;
  try {
    reponse = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": Deno.env.get("ANTHROPIC_API_KEY")!,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: modele,
        max_tokens: Math.min(Number(corps.max_tokens) || MAX_TOKENS, MAX_TOKENS),
        system: corps.system,
        messages,
        tools: [{ type: "web_search_20250305", name: "web_search", max_uses: 3 }],
      }),
    });
  } catch (_e) {
    return json({ erreur: "IA injoignable" }, 502);
  }
  if (!reponse.ok) {
    return json({ erreur: "Erreur IA", statut: reponse.status }, 502);
  }
  const resultat = await reponse.json();

  // 5. Décompter une consultation SEULEMENT après un appel réussi (RPC atomique)
  await service.rpc("consommer_credit", { p_user: userId });

  return json({ resultat, solde: solde - 1 });
});
