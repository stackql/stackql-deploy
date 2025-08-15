// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from 'prism-react-renderer';

const providerDropDownListItems = [
  {
    label: 'AWS',
    to: '/providers/aws',
  },
  {
    label: 'Azure',
    to: '/providers/azure',
  },
  {
    label: 'Google',
    to: '/providers/google',
  },
  {
    label: 'Databricks',
    to: '/providers/databricks',
  },
  {
    label: 'Snowflake',
    to: '/providers/snowflake',
  },
  {
    label: 'Confluent',
    to: '/providers/confluent',
  },
  {
    label: 'Okta',
    to: '/providers/okta',
  },
  {
    label: 'GitHub',
    to: '/providers/github',
  },
  {
    label: 'OpenAI',
    to: '/providers/openai',
  },
  {
    label: '... More',
    to: '/providers',
  },
];

const footerStackQLItems = [
  {
    label: 'Documentation',
    to: '/stackqldocs',
  },
  {
    label: 'Install',
    to: '/install',
  },
  {
    label: 'Contact us',
    to: '/contact-us',
  },
];

const footerMoreItems = [
  {
    label: 'Providers',
    to: '/providers',
  },
  {
    label: 'stackql-deploy',
    to: '/stackql-deploy',
  },            
  {
    label: 'Blog',
    to: '/blog',
  },
  {
    label: 'Tutorials',
    to: '/tutorials',
  },            
];


/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'StackQL Deploy',
  // baseUrl: '/stackql-deploy/',
  baseUrl: '/',
  tagline: 'Deploy and Test Cloud and SaaS Environments using StackQL',
  favicon: 'img/favicon.ico',
  staticDirectories: ['static'],
  url: 'https://stackql-deploy.io',
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
          routeBasePath: '/', // Set the docs to be the root of the site
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
          alt: 'StackQL Deploy',
          href: '/',
          src: 'img/stackql-deploy-logo.svg',
          srcDark: 'img/stackql-deploy-logo-white.svg',
        },
        items: [
          // {
          //   type: 'docSidebar',
          //   sidebarId: 'docsSidebar',
          //   position: 'left',
          //   label: 'Deploy Docs',
          // },
          {
            to: '/install',
            position: 'left',
            label: 'Install',
          },
          {
            to: '/stackqldocs',
            position: 'left',
            label: 'StackQL Docs',
          },          
          {
            to: '/providers',
            type: 'dropdown',
            label: 'Providers',
            position: 'left',
            items: providerDropDownListItems,                      
          },
          {
            type: 'dropdown',
            label: 'More',
            position: 'left',
            items: [
            {
              to: '/blog',
              label: 'Blog',
            },
            {
              to: '/tutorials',
              label: 'Tutorials',
            },
            ],
          },
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
          href: '/',
          src: 'img/stackql-deploy-logo.svg',
          srcDark: 'img/stackql-deploy-logo-white.svg',
        },
        links: [
          {
            title: 'StackQL',
            items: footerStackQLItems,
          },
          {
            title: 'More',
            items: footerMoreItems,
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
