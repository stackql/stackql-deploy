import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';

function CustomSidebarCategory({icon, label, description, to}) {
  return React.createElement(
    'div',
    { className: 'sidebar-item' },
    React.createElement(
      Link,
      { className: clsx('menu__link'), to: to },
      React.createElement('img', { src: icon, alt: label, style: { width: '24px', marginRight: '10px' } }),
      React.createElement(
        'div',
        { className: 'sidebar-item-content' },
        React.createElement('div', { className: 'sidebar-item-label' }, label),
        React.createElement('div', { className: 'sidebar-item-description' }, description)
      )
    )
  );
}

export default CustomSidebarCategory;
