const initialNodes = [
  {
    id: '1',
    data: {
      label: (
        <>
          <strong>Incident Declared</strong>
        </>
      )
    },
    type: 'input',
    position: { x: 1, y: 1 },
    style: {
      background: '#D6D5E6',
      color: '#333',
      border: 'wpx solid #222138',
      width: 180
    }
  },
  {
    id: '2',
    data: { label: 'Slack Channel Created' },
    position: { x: 100, y: 60 },
    style: {
      background: '#D6D5E6',
      color: '#333',
      border: 'wpx solid #222138',
      width: 180
    }
  },
  {
    id: '3',
    data: { label: 'Incident Advertised' },
    position: { x: 200, y: 120 },
    style: {
      background: '#D6D5E6',
      color: '#333',
      border: 'wpx solid #222138',
      width: 180
    }
  },
  {
    id: '4',
    data: { label: 'Initiator Invited' },
    position: { x: 300, y: 180 },
    style: {
      background: '#D6D5E6',
      color: '#333',
      border: 'wpx solid #222138',
      width: 180
    }
  },
  {
    id: '5',
    data: { label: 'Page Sent Out' },
    position: { x: 400, y: 240 },
    style: {
      background: '#D6D5E6',
      color: '#333',
      border: 'wpx solid #222138',
      width: 180
    }
  },
  {
    id: '6',
    data: { label: 'Listen for Changes' },
    position: { x: 500, y: 300 },
    style: {
      background: '#D6D5E6',
      color: '#333',
      border: 'wpx solid #222138',
      width: 180
    }
  }
];

export default initialNodes;
