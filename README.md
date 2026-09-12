# Analytics Foot — Backend FastAPI

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # puis remplir les valeurs (clés Supabase, SenePay, SMTP)
```

## Lancer en local

```bash
uvicorn app.main:app --reload
```

Documentation interactive : http://localhost:8000/docs

## Structure

```
app/
  main.py              # point d'entrée, assemble les routers
  config.py            # variables d'environnement (Settings)
  database.py          # client Supabase (service_role)
  deps.py              # auth + contrôle de rôle (admin/user/affiliate)
  schemas.py           # modèles Pydantic (requêtes/réponses)
  routers/
    auth.py            # inscription / connexion / profil
    subscriptions.py   # Pass VIP (journée/semaine/mensuel)
    payments.py        # intégration SenePay (payin + webhook)
    predictions.py     # pronostics, combinés, packs utilisateurs
    affiliates.py       # stats affilié, retraits (OTP -> validation admin)
  utils/
    email.py           # envoi des codes OTP par e-mail
  jobs/
    weekly_payout.py        # traitement hebdo des retraits affiliés (dimanche 00h05)
    reconcile_payments.py   # filet de sécurité si le webhook SenePay échoue (toutes les 10 min)
    expire_subscriptions.py # expire les Pass VIP dépassés (toutes les heures)
  scheduler.py               # démarre ces 3 jobs en arrière-plan au lancement du serveur
```

## Tâches en arrière-plan

Dès que le serveur démarre (`uvicorn app.main:app`), 3 jobs tournent en
continu sans intervention manuelle, via APScheduler :

| Job | Fréquence | Rôle |
|---|---|---|
| `reconcile_pending_payments` | toutes les 10 min | Interroge SenePay pour les paiements restés `pending` (si le webhook n'est jamais arrivé) |
| `expire_outdated_subscriptions` | toutes les heures | Passe les Pass VIP dépassés en `expired` |
| `run_weekly_payout_batch` | dimanche 00h05 | Prépare les retraits affiliés confirmés (OTP validé) pour la validation admin |

⚠️ En production, si tu déploies sur plusieurs instances du serveur en
parallèle (scaling horizontal), il faut faire tourner ces jobs sur **une
seule instance** (ou migrer vers un scheduler externe partagé) pour éviter
les doublons.

## Points à finaliser avant la production

- [ ] Vérifier les noms exacts des champs de l'API SenePay
      (https://api.sene-pay.com/docs.html) dans `payments.py` et
      `affiliates.py` (endpoints `/payin` et `/payout`) — les noms utilisés
      ici sont indicatifs et doivent être confirmés.
- [ ] Planifier `jobs/weekly_payout.py` (cron système ou Supabase
      Edge Function cron) pour qu'il tourne chaque dimanche.
- [ ] Restreindre `allow_origins` dans `main.py` au domaine réel du frontend.
- [ ] Ajouter la pagination sur les listes (predictions, withdrawals) avant
      un volume de données important.

## Tableau de bord admin — retraits et suivi des payouts

- `GET /affiliates/admin/payout-stats` — nombre et montant total des
  payouts déjà effectués aujourd'hui, avec le quota restant par rapport
  aux plafonds du contrat SenePay (100/jour, 50 000 000 FCFA/jour).
- `GET /affiliates/admin/withdrawals` — liste des demandes de retrait en
  attente de validation (OTP déjà confirmé par l'affilié).
- `POST /affiliates/withdrawals/{id}/admin-approve` — déclenche le vrai
  virement SenePay (vérifie d'abord les plafonds), utilisable à tout moment
  depuis le dashboard admin, pas seulement le dimanche.
