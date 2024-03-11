import React from 'react';
import PersistentDrawerLeft from '../components/AppDrawer.component';

export const WithNav = ({ children }) => {
  return (
    <>
      <PersistentDrawerLeft />
      {children}
    </>
  );
};
