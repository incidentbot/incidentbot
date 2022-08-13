export function tryParseJSONObject(jsonString) {
  try {
    var o = JSON.parse(jsonString);
    if (o && typeof o === 'object') {
      return true;
    }
  } catch (e) {
    console.log('not a json object');
  }
  return false;
}
