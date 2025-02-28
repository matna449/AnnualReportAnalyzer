'use client';

import React from 'react';
import { Box, Container } from '@mui/material';
import DashboardNavbar from './DashboardNavbar';
import Footer from './Footer';

interface PageLayoutProps {
  children: React.ReactNode;
}

const PageLayout: React.FC<PageLayoutProps> = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <DashboardNavbar />
      
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
        {children}
      </Container>
      
      <Footer />
    </Box>
  );
};

export default PageLayout;
