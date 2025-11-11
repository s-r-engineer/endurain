import {
  fetchDeleteRequest,
  fetchPutRequest
} from '@/utils/serviceUtils'

const POLAR_AUTH_URL = 'https://flow.polar.com/oauth2/authorization'
const POLAR_SCOPE = 'accesslink.read_all'

export const polar = {
  setUniqueUserStatePolarLink(state) {
    return fetchPutRequest(`polar/state/${state}`)
  },
  setUserPolarClientSettings(clientId, clientSecret) {
    const data = {
      client_id: clientId,
      client_secret: clientSecret
    }
    return fetchPutRequest('polar/client', data)
  },
  linkPolar(state, clientId) {
    let redirectUri = `${window.env.ENDURAIN_HOST}`
    redirectUri = encodeURIComponent(`${redirectUri}/polar/callback`)
    const polarAuthUrl = `${POLAR_AUTH_URL}?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=${POLAR_SCOPE}&state=${state}`
    window.location.href = polarAuthUrl
  },
  linkPolarCallback(state, code) {
    return fetchPutRequest(`polar/link?state=${state}&code=${code}`)
  },
  unlinkPolar() {
    return fetchDeleteRequest('polar/unlink')
  }
}
