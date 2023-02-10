import { Button } from '@mui/material';

import ArticleIcon from '@mui/icons-material/Article';

const docsLink = 'https://docs.incidentbot.io';

export default function ViewDocsButton() {
  return (
    <div>
      <Button
        variant="contained"
        color="info"
        size="medium"
        endIcon={<ArticleIcon />}
        href={docsLink}
        target="new"
        sx={{
          display: { xs: 'none', md: 'flex' },
          marginLeft: 2,
          marginRight: 2
        }}>
        Documentation
      </Button>
      <Button
        variant="contained"
        color="info"
        size="medium"
        endIcon={<ArticleIcon />}
        href={docsLink}
        target="new"
        sx={{
          display: { xs: 'flex', md: 'none' },
          marginLeft: 2,
          marginRight: 2
        }}>
        Docs
      </Button>
    </div>
  );
}
