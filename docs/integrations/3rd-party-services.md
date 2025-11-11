# 3rd party services

---

## Garmin Connect Integration

To enable Garmin Connect integration, Endurain will ask for your Garmin Connect credentials. These credentials are not stored, but the authentication tokens (access and refresh tokens) are stored in the DB, similar to the Strava integration. The credentials are sent from the frontend to the backend in plain text, so the use of HTTPS is highly recommended.

Once the integration with Garmin Connect is configured, on startup, every one and four hours the backend will check if there is new unimported activities and new body composition entries respectively. If yes, the new data is automatically imported.

For Garmin Connect integration [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) Python module is used.

## Strava Integration

> ⚠️ **Warning**  
> Due to recent Strava API changes, expect changes in the Strava integration in a following release.

To enable Strava integration, ensure your Endurain instance is accessible from the internet and follow Strava's [API setup guide](https://developers.strava.com/docs/getting-started/). After the integration is successful the access and refresh tokens are stored in the DB. Each user will have his/hers own pair.

Once the integration with Strava is configured, on startup and every hour the backend will check if there is new unimported activities. If yes, the new activity is automatically imported.

On link, user will need to provide his/her API client ID and secret. Pair will be temporary stored in the DB until the process finishes. Info is sent on a JSON payload and HTTPS end2end is encouraged.

On Strava unlink action every data imported from Strava, i.e. activities and gears, will be deleted according to Strava [API Agreement](https://www.strava.com/legal/api).

For Strava integration [stravalib](https://github.com/stravalib/stravalib) Python module is used.

## Polar AccessLink Integration

Polar AccessLink support follows a similar OAuth flow: each user provides the Client ID and Client secret of their Polar application and approves access through Polar Flow. Once the authorization code is exchanged, access tokens are stored encrypted in the database for future API calls.

Polar activities are ingested through [AccessLink webhooks](https://www.polar.com/accesslink-api/#accesslink-webhooks). To configure the integration:

1. Create an API client in [Polar's AccessLink admin](https://admin.polaraccesslink.com/) and add a redirect URL pointing to `https://<your-domain>/polar/callback`.
2. Create a webhook that targets `https://<your-domain>/api/v1/polar/webhook`. Copy the signature secret key that is shown once and set it as the `POLAR_WEBHOOK_SECRET` environment variable (or `POLAR_WEBHOOK_SECRET_FILE` for Docker secrets). This key is required to verify incoming webhook payloads.
3. Share the Client ID and Client secret with the Endurain user that will link Polar. These values are encrypted and kept until the link or relink process finishes.

Whenever Polar notifies Endurain about a new exercise, Endurain downloads the original GPX from AccessLink and imports it automatically—no manual refresh endpoint is required. Unlinking Polar removes every activity that was imported from AccessLink for that user.

Polar AccessLink requests are implemented with standard `requests` calls in the backend.
