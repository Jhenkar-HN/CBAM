import {
  Bell,
  BookOpen,
  Building2,
  ClipboardCheck,
  FileCheck2,
  HelpCircle,
  Monitor,
  Palette,
  Scale,
  Settings,
  ShieldCheck,
  Upload,
  UserCog,
  Wrench,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'Plant Manager',
    email: 'plant.manager@example.com',
    avatar: '/avatars/shadcn.jpg',
  },
  teams: [
    {
      name: 'CBAM Passport',
      logo: ShieldCheck,
      plan: 'Emissions evidence workspace',
    },
  ],
  navGroups: [
    {
      title: 'Workflow',
      items: [
        {
          title: 'Workspace',
          url: '/workspace',
          icon: Building2,
        },
        {
          title: 'Upload records',
          url: '/upload',
          icon: Upload,
        },
        {
          title: 'Review extraction',
          url: '/review',
          icon: ClipboardCheck,
        },
        {
          title: 'Mass allocation',
          url: '/allocation',
          icon: Scale,
        },
        {
          title: 'Emissions passport',
          url: '/passport',
          icon: FileCheck2,
        },
      ],
    },
    {
      title: 'Guidance',
      items: [
        {
          title: 'Regulatory assistant',
          url: '/assistant',
          icon: BookOpen,
        },
      ],
    },
    {
      title: 'Other',
      items: [
        {
          title: 'Settings',
          icon: Settings,
          items: [
            {
              title: 'Profile',
              url: '/settings',
              icon: UserCog,
            },
            {
              title: 'Account',
              url: '/settings/account',
              icon: Wrench,
            },
            {
              title: 'Appearance',
              url: '/settings/appearance',
              icon: Palette,
            },
            {
              title: 'Notifications',
              url: '/settings/notifications',
              icon: Bell,
            },
            {
              title: 'Display',
              url: '/settings/display',
              icon: Monitor,
            },
          ],
        },
        {
          title: 'Help center',
          url: '/help-center',
          icon: HelpCircle,
        },
      ],
    },
  ],
}
