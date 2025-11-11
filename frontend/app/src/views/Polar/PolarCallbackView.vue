<template>
  <div class="text-center">
    <LoadingComponent />
    <br />
    <p>{{ $t('polarCallbackView.polarCallbackViewTitle1') }}</p>
    <p>{{ $t('polarCallbackView.polarCallbackViewTitle2') }}</p>
  </div>
</template>

<script>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { push } from 'notivue'
import { useRoute, useRouter } from 'vue-router'
import LoadingComponent from '@/components/GeneralComponents/LoadingComponent.vue'
import { polar } from '@/services/polarService'

export default {
  components: {
    LoadingComponent
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const { t } = useI18n()

    onMounted(async () => {
      if (route.query.state && route.query.code) {
        try {
          await polar.linkPolarCallback(route.query.state, route.query.code)

          return router.push({
            path: '/settings',
            query: { polarLinked: '1' }
          })
        } catch (error) {
          push.error(`${t('settingsIntegrationsZone.errorMessageUnableToLinkPolar')} - ${error}`)

          return router.push({
            path: '/settings',
            query: { polarLinked: '0' }
          })
        }
      }
    })
  }
}
</script>
