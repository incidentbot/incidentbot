import { titleCase } from './titleCase.js';

export function formatRoleName(role) {
  var formatted = '';

  role.split('_').forEach(function (word) {
    formatted += `${titleCase(word)} `;
  });

  return formatted;
}
