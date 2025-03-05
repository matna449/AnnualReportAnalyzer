'use client';

import React, { useState, useEffect } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Box, 
  IconButton,
  useMediaQuery,
  useTheme,
  Menu,
  MenuItem,
  FormControlLabel,
  Switch
} from '@mui/material';
import { 
  Dashboard as DashboardIcon, 
  Search as SearchIcon, 
  CompareArrows as CompareIcon,
  Home as HomeIcon,
  Menu as MenuIcon
} from '@mui/icons-material';
import Link from 'next/link';
import { isAdmin } from '@/utils/featureFlags';

const DashboardNavbar: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isAdminUser, setIsAdminUser] = useState(false);
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  useEffect(() => {
    // Check if user is admin on component mount
    setIsAdminUser(isAdmin());
  }, []);
  
  const toggleAdminMode = () => {
    const newAdminStatus = !isAdminUser;
    localStorage.setItem('isAdmin', newAdminStatus.toString());
    setIsAdminUser(newAdminStatus);
    // Reload the page to apply changes
    window.location.reload();
  };

  return (
    <AppBar position="static" color="default" elevation={1} sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          <Link href="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center' }}>
            <DashboardIcon sx={{ mr: 1 }} />
            Annual Report Analyzer
          </Link>
        </Typography>
        
        {isMobile ? (
          <>
            <IconButton
              size="large"
              edge="end"
              color="inherit"
              aria-label="menu"
              onClick={handleMenuOpen}
            >
              <MenuIcon />
            </IconButton>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
            >
              <MenuItem onClick={handleMenuClose} component={Link} href="/">
                <HomeIcon fontSize="small" sx={{ mr: 1 }} />
                Home
              </MenuItem>
              <MenuItem onClick={handleMenuClose} component={Link} href="/dashboard">
                <DashboardIcon fontSize="small" sx={{ mr: 1 }} />
                Dashboard
              </MenuItem>
              <MenuItem onClick={handleMenuClose} component={Link} href="/search">
                <SearchIcon fontSize="small" sx={{ mr: 1 }} />
                Search
              </MenuItem>
              <MenuItem onClick={handleMenuClose} component={Link} href="/compare">
                <CompareIcon fontSize="small" sx={{ mr: 1 }} />
                Compare
              </MenuItem>
            </Menu>
          </>
        ) : (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button 
              color="inherit" 
              startIcon={<HomeIcon />}
              component={Link}
              href="/"
            >
              Home
            </Button>
            <Button 
              color="inherit" 
              startIcon={<DashboardIcon />}
              component={Link}
              href="/dashboard"
            >
              Dashboard
            </Button>
            <Button 
              color="inherit" 
              startIcon={<SearchIcon />}
              component={Link}
              href="/search"
            >
              Search
            </Button>
            <Button 
              color="inherit" 
              startIcon={<CompareIcon />}
              component={Link}
              href="/compare"
            >
              Compare
            </Button>
          </Box>
        )}
        
        {isDevelopment && (
          <FormControlLabel
            control={
              <Switch
                checked={isAdminUser}
                onChange={toggleAdminMode}
                color="primary"
              />
            }
            label="Admin Mode"
            sx={{ ml: 2, display: { xs: 'none', md: 'flex' } }}
          />
        )}
      </Toolbar>
    </AppBar>
  );
};

export default DashboardNavbar; 