// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'StackQL Deploy',
  tagline: 'Deploy and Test Cloud and SaaS Environments using StackQL',
  favicon: 'img/favicon.ico',
  staticDirectories: ['static'],
  url: 'https://stackql-deploy.io',
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  organizationName: 'stackql',
  projectName: 'stackql-deploy',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          // Remove this to remove the "edit this page" links.
          editUrl: 'https://github.com/stackql/stackql-deploy/tree/main/website/',
        },
        // blog: {
        //   showReadingTime: true,
        //   feedOptions: {
        //     type: ['rss', 'atom'],
        //     xslt: true,
        //   },
        //   // Remove this to remove the "edit this page" links.
        //   editUrl:
        //     'https://github.com/stackql/stackql-deploy/tree/main/website/',
        // },
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/stackql-cover.png',
      navbar: {
        logo: {
          alt: 'StackQL',
          href: '/docs',
          src: 'img/logo-original.svg',
          srcDark: 'img/logo-white.svg',
        },        
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Deploy Docs',
          },
          {
            to: '/stackqldocs',
            position: 'left',
            label: 'StackQL Docs',
          },          
          {
            to: '/registry',
            type: 'dropdown',
            label: 'StackQL Providers',
            position: 'left',
            items: [
              {
                label: 'AWS',
                to: '/registry/aws',
              },
              {
                label: 'Azure',
                to: '/registry/azure',
              },
              {
                label: 'Google',
                to: '/registry/google',
              },
              {
                label: 'GitHub',
                to: '/registry/github',
              },
              {
                label: 'Kubernetes',
                to: '/registry/k8s',
              },
              {
                label: 'Okta',
                to: '/registry/okta',
              },
              {
                label: 'DigitalOcean',
                to: '/registry/digitalocean',
              },
              {
                label: 'Linode',
                to: '/registry/linode',
              },
              {
                label: '... More',
                to: '/registry',
              },                                                                                                
            ]                      
          },          
          // {to: '/blog', label: 'Blog', position: 'left'},
          {
            href: 'https://github.com/stackql/stackql',
            position: 'right',
            className: 'header-github-link',
            'aria-label': 'GitHub repository',
          },          
        ],
      },
      footer: {
        style: 'dark',
        logo: {
          alt: 'StackQL',
          href: 'https://stackql.io/',
          src: 'img/logo-original.svg',
          srcDark: 'img/logo-white.svg',
        },
        links: [
          {
            title: 'StackQL',
            items: [
              {
                label: 'Home',
                to: '/home',
              },
              {
                label: 'Features',
                to: '/features',
              },
              {
                label: 'Downloads',
                to: '/downloads',
              },
              {
                label: 'Contact us',
                href: '/contact-us',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'StackQL Docs',
                to: '/stackqldocs',
              },
              {
                label: 'Providers',
                to: '/registry',
              },
              {
                label: 'Blog',
                to: '/blog',
              },
            ],
          },
        ],
        copyright: `© ${new Date().getFullYear()} StackQL Studios`,
      },  
      colorMode: {
        // using user system preferences, instead of the hardcoded defaultMode
        respectPrefersColorScheme: true,
      },          
      prism: {
        theme: prismThemes.nightOwl,
        darkTheme: prismThemes.dracula,
      },
    }),
};

export default config;
