<script setup lang="ts">
import { computed } from 'vue'

import alertCircleIcon from 'feather-icons/dist/icons/alert-circle.svg?raw'
import alertTriangleIcon from 'feather-icons/dist/icons/alert-triangle.svg?raw'
import archiveIcon from 'feather-icons/dist/icons/archive.svg?raw'
import arrowLeftIcon from 'feather-icons/dist/icons/arrow-left.svg?raw'
import arrowRightIcon from 'feather-icons/dist/icons/arrow-right.svg?raw'
import checkIcon from 'feather-icons/dist/icons/check.svg?raw'
import checkCircleIcon from 'feather-icons/dist/icons/check-circle.svg?raw'
import compassIcon from 'feather-icons/dist/icons/compass.svg?raw'
import editIcon from 'feather-icons/dist/icons/edit-3.svg?raw'
import heartIcon from 'feather-icons/dist/icons/heart.svg?raw'
import inboxIcon from 'feather-icons/dist/icons/inbox.svg?raw'
import infoIcon from 'feather-icons/dist/icons/info.svg?raw'
import logOutIcon from 'feather-icons/dist/icons/log-out.svg?raw'
import mailIcon from 'feather-icons/dist/icons/mail.svg?raw'
import plusIcon from 'feather-icons/dist/icons/plus.svg?raw'
import refreshIcon from 'feather-icons/dist/icons/refresh-cw.svg?raw'
import retryIcon from 'feather-icons/dist/icons/rotate-ccw.svg?raw'
import saveIcon from 'feather-icons/dist/icons/save.svg?raw'
import searchIcon from 'feather-icons/dist/icons/search.svg?raw'
import sendIcon from 'feather-icons/dist/icons/send.svg?raw'
import settingsIcon from 'feather-icons/dist/icons/settings.svg?raw'
import shieldIcon from 'feather-icons/dist/icons/shield.svg?raw'
import slidersIcon from 'feather-icons/dist/icons/sliders.svg?raw'
import sunIcon from 'feather-icons/dist/icons/sun.svg?raw'
import userIcon from 'feather-icons/dist/icons/user.svg?raw'
import userPlusIcon from 'feather-icons/dist/icons/user-plus.svg?raw'
import usersIcon from 'feather-icons/dist/icons/users.svg?raw'
import userXIcon from 'feather-icons/dist/icons/user-x.svg?raw'
import xIcon from 'feather-icons/dist/icons/x.svg?raw'
import xCircleIcon from 'feather-icons/dist/icons/x-circle.svg?raw'

const iconMarkup = {
  'alert-circle': alertCircleIcon,
  'alert-triangle': alertTriangleIcon,
  archive: archiveIcon,
  'arrow-left': arrowLeftIcon,
  'arrow-right': arrowRightIcon,
  check: checkIcon,
  'check-circle': checkCircleIcon,
  compass: compassIcon,
  'edit-3': editIcon,
  heart: heartIcon,
  inbox: inboxIcon,
  info: infoIcon,
  'log-out': logOutIcon,
  mail: mailIcon,
  plus: plusIcon,
  'refresh-cw': refreshIcon,
  'rotate-ccw': retryIcon,
  save: saveIcon,
  search: searchIcon,
  send: sendIcon,
  settings: settingsIcon,
  shield: shieldIcon,
  sliders: slidersIcon,
  sun: sunIcon,
  user: userIcon,
  'user-plus': userPlusIcon,
  users: usersIcon,
  'user-x': userXIcon,
  x: xIcon,
  'x-circle': xCircleIcon,
} as const

type AppIconName = keyof typeof iconMarkup

const props = withDefaults(
  defineProps<{
    name: AppIconName
    size?: number | string
    strokeWidth?: number | string
  }>(),
  {
    size: 20,
    strokeWidth: 2,
  },
)

const markup = computed(() => iconMarkup[props.name])

const iconStyle = computed(() => ({
  '--icon-size': typeof props.size === 'number' ? `${props.size}px` : props.size,
  '--icon-stroke-width': props.strokeWidth,
}))
</script>

<template>
  <span class="feather-icon" :style="iconStyle" aria-hidden="true" v-html="markup"></span>
</template>

<style scoped>
.feather-icon {
  display: inline-grid;
  width: var(--icon-size);
  height: var(--icon-size);
  flex: 0 0 auto;
  place-items: center;
  line-height: 0;
}

.feather-icon :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
  stroke-width: var(--icon-stroke-width);
}
</style>
