// import React from 'react';
// import Head from '@docusaurus/Head';

// export default function Home() {
//   return (
//     <Head>
//     <meta http-equiv="refresh" content="0;URL='https://stackql.io/'" />
//     </Head>
//   );
// }


import React from 'react';
import Layout from '@theme/Layout';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  
  return (
    <Layout
      title={siteConfig.title}
      description="StackQL Deploy">
      <main className="container margin-vert--xl">
        <div className="text-center">
          <h1>StackQL Deploy</h1>
          <p>Development Mode</p>
        </div>
      </main>
    </Layout>
  );
}