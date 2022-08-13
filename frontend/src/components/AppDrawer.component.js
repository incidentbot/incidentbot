import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Box,
  CssBaseline,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar
} from '@mui/material';

import MuiDrawer from '@mui/material/Drawer';
import MuiAppBar from '@mui/material/AppBar';

import AddTaskIcon from '@mui/icons-material/AddTask';
import AnnouncementIcon from '@mui/icons-material/Announcement';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DashboardIcon from '@mui/icons-material/Dashboard';
import MenuIcon from '@mui/icons-material/Menu';
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid';
import SettingsIcon from '@mui/icons-material/Settings';

import { styled, useTheme } from '@mui/material/styles';
import { blue, blueGrey } from '@mui/material/colors';

import AvatarMenu from './Avatar-menu.component';
import { apiUrl } from '../shared/Variables';
import { ThemeToggle } from './ThemeToggle.component';
import ApplicationHeaderLogo from './Header-logo.component';
import { severities } from '../shared/Variables';
import IncidentCreateModal from './Create-incident-modal.component';

const drawerWidth = 240;

const openedMixin = (theme) => ({
  width: drawerWidth,
  transition: theme.transitions.create('width', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.enteringScreen
  }),
  overflowX: 'hidden'
});

const closedMixin = (theme) => ({
  transition: theme.transitions.create('width', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen
  }),
  overflowX: 'hidden',
  width: `calc(${theme.spacing(7)} + 1px)`,
  [theme.breakpoints.up('sm')]: {
    width: `calc(${theme.spacing(8)} + 1px)`
  }
});

const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  padding: theme.spacing(0, 1),
  // necessary for content to be below app bar
  ...theme.mixins.toolbar
}));

const AppBar = styled(MuiAppBar, {
  shouldForwardProp: (prop) => prop !== 'open'
})(({ theme, open }) => ({
  zIndex: theme.zIndex.drawer + 1,
  transition: theme.transitions.create(['width', 'margin'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen
  }),
  ...(open && {
    marginLeft: drawerWidth,
    width: `calc(100% - ${drawerWidth}px)`,
    transition: theme.transitions.create(['width', 'margin'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen
    })
  })
}));

const Drawer = styled(MuiDrawer, { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    width: drawerWidth,
    flexShrink: 0,
    whiteSpace: 'nowrap',
    boxSizing: 'border-box',
    ...(open && {
      ...openedMixin(theme),
      '& .MuiDrawer-paper': openedMixin(theme)
    }),
    ...(!open && {
      ...closedMixin(theme),
      '& .MuiDrawer-paper': closedMixin(theme)
    })
  })
);

const NavigationItemButton = styled(ListItemButton)(() => ({
  minHeight: 48,
  justifyContent: open ? 'initial' : 'center',
  px: 2.5,
  ...(sessionStorage.getItem('theme') === 'dark' && {
    '&:hover': {
      backgroundColor: blueGrey[600],
      color: blueGrey[900]
    }
  }),
  ...(sessionStorage.getItem('theme') === 'light' && {
    '&:hover': {
      backgroundColor: blue[200],
      color: blueGrey[900]
    }
  })
}));

const PrimaryMenuItems = [
  { title: 'Dashboard', link: '/app', icon: <DashboardIcon /> },
  { title: 'Incidents', link: '/app/incidents', icon: <AnnouncementIcon /> },
  { title: 'On-Call', link: '/app/on-call', icon: <PhoneAndroidIcon /> },
  { title: 'Jobs', link: '/app/jobs', icon: <AddTaskIcon /> },
  { title: 'Settings', link: '/app/settings', icon: <SettingsIcon /> }
];

export default function MiniDrawer() {
  const theme = useTheme();

  const drawerStateKey = 'drawerOpen';
  const defaultOpen = sessionStorage.getItem(drawerStateKey) === 'true';
  const [open, setOpen] = useState(defaultOpen);

  let location = useLocation();

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  useEffect(() => {
    sessionStorage.setItem(drawerStateKey, open);
  }, [open]);

  return (
    <>
      <Box sx={{ display: 'flex' }}>
        <CssBaseline />
        <AppBar position="fixed" open={open} color="primary">
          <Toolbar>
            <Box sx={{ display: 'flex', flexGrow: 1 }}>
              <IconButton
                color="inherit"
                aria-label="open drawer"
                onClick={handleDrawerOpen}
                edge="start"
                sx={{
                  marginRight: 5,
                  ...(open && { display: 'none' })
                }}>
                <MenuIcon />
              </IconButton>
              {!open && <ApplicationHeaderLogo />}
            </Box>
            <IncidentCreateModal apiUrl={apiUrl} severities={severities} />
            <AvatarMenu />
          </Toolbar>
        </AppBar>
        <Drawer variant="permanent" open={open}>
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <DrawerHeader>
              <ApplicationHeaderLogo />
              <IconButton onClick={handleDrawerClose}>
                {theme.direction === 'rtl' ? <ChevronRightIcon /> : <ChevronLeftIcon />}
              </IconButton>
            </DrawerHeader>
            <Divider variant="middle" />
            <List>
              <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                {PrimaryMenuItems.map((item) => (
                  <ListItem key={item.title.toLowerCase()} disablePadding sx={{ display: 'block' }}>
                    <NavigationItemButton
                      selected={
                        location.pathname === '/' && item.title === 'Dashboard'
                          ? true
                          : location.pathname === `/${item.title.toLowerCase()}`
                      }
                      href={item.link ? item.link : null}>
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: open ? 3 : 'auto',
                          justifyContent: 'center'
                        }}>
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText
                        primary={item.title.toUpperCase()}
                        sx={{ opacity: open ? 1 : 0 }}
                        primaryTypographyProps={{
                          fontFamily: 'Roboto',
                          fontWeight: 100,
                          letterSpacing: '.1rem',
                          color: 'inherit',
                          textDecoration: 'none'
                        }}
                      />
                    </NavigationItemButton>
                  </ListItem>
                ))}
              </Box>
              <Box
                sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <ListItem key={`theme-toggle`} disablePadding sx={{ display: 'block' }}>
                  <ThemeToggle />
                </ListItem>
              </Box>
            </List>
          </Box>
        </Drawer>
      </Box>
    </>
  );
}
