import React from 'react';
import { Box, Container } from '@mui/material';
import ThemeProvider from './ThemeProvider';
import DashboardNavbar from './DashboardNavbar';
import Footer from './Footer';

interface PageLayoutProps {
  children: React.ReactNode;
}

const PageLayout: React.FC<PageLayoutProps> = ({ children }) => {
  return (
    <ThemeProvider>
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <DashboardNavbar />
        
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
          {children}
        </Container>
        
        <Footer />
      </Box>
    </ThemeProvider>
  );
};

export default PageLayout;
