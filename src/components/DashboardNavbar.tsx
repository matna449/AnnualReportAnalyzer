import React from 'react';
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
  MenuItem
} from '@mui/material';
import { 
  Dashboard as DashboardIcon, 
  Search as SearchIcon, 
  CompareArrows as CompareIcon,
  Home as HomeIcon,
  Menu as MenuIcon
} from '@mui/icons-material';
import Link from 'next/link';

const DashboardNavbar: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <AppBar position="static" color="default" elevation={1}>
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
      </Toolbar>
    </AppBar>
  );
};

export default DashboardNavbar; 