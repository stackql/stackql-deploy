import React from 'react';
import Head from '@docusaurus/Head';

export default function DocsRedirect() {
  return (
    <Head>
    <meta http-equiv="refresh" content="0;URL='/'" />
    </Head>
  );
};