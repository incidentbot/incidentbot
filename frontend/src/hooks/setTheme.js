import { createTheme } from '@mui/material/styles';
import { blue, blueGrey, grey, lightBlue } from '@mui/material/colors';

export function setTheme(themeName) {
  sessionStorage.setItem('theme', themeName);
  document.documentElement.className = themeName;
}

export let abGradientPerTheme, acGradientPerTheme, gradientBase;

export function keepTheme() {
  if (sessionStorage.getItem('theme')) {
    if (sessionStorage.getItem('theme') === 'dark') {
      setTheme('dark');
      abGradientPerTheme = `linear-gradient(to right, #1B4F72, #5DADE2)`;
      acGradientPerTheme = 'linear-gradient(to right, #808B96, #121212)';
      gradientBase = `#000000`;
    } else if (sessionStorage.getItem('theme') === 'light') {
      setTheme('light');
      abGradientPerTheme = `linear-gradient(to right, #01579B, #89CFF0)`;
      acGradientPerTheme = 'linear-gradient(to right, #ffffff, #0173cd)';
      gradientBase = `#ffffff`;
    }
  } else {
    setTheme('dark');
  }
}

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: blueGrey,
    info: {
      main: lightBlue[700],
      light: lightBlue[200]
    },
    divider: blueGrey[700],
    background: {
      default: blueGrey[900],
      paper: blueGrey[900]
    },
    text: {
      primary: '#fff',
      secondary: grey[500]
    }
  },
  components: {
    MuiListItemButton: {
      styleOverrides: {
        root: () => ({
          '&.Mui-selected': {
            backgroundColor: blueGrey[800],
            color: lightBlue[100],
            '.MuiListItemIcon-root': {
              color: lightBlue[100]
            }
          }
        })
      }
    }
  },
  root: {
    flexGrow: 1,
    width: '100%'
  }
});

const lightTheme = createTheme({
  palette: {
    mode: 'light'
  },
  components: {
    MuiListItemButton: {
      styleOverrides: {
        root: () => ({
          '&.Mui-selected': {
            backgroundColor: blue[700],
            color: lightBlue[100],
            '.MuiListItemIcon-root': {
              color: lightBlue[100]
            }
          }
        })
      }
    }
  },
  root: {
    flexGrow: 1,
    width: '100%'
  }
});

export function setThemeParameters() {
  if (sessionStorage.getItem('theme')) {
    if (sessionStorage.getItem('theme') === 'dark') {
      return darkTheme;
    } else if (sessionStorage.getItem('theme') === 'light') {
      return lightTheme;
    } else {
      return darkTheme;
    }
  }
}
