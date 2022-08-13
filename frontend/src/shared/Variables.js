export const apiUrl = process.env.REACT_APP_BACKEND_API_URL
  ? process.env.REACT_APP_BACKEND_API_URL
  : '/api/v1';

// This should probably be returned from Slack so it's all managed in the same place
export const severities = ['sev1', 'sev2', 'sev3', 'sev4'];

export const statuses = ['investigating', 'identified', 'monitoring', 'resolved'];
