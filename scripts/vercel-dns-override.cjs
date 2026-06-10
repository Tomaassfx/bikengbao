const dns = require("node:dns");

const originalLookup = dns.lookup.bind(dns);
const originalPromisesLookup = dns.promises.lookup.bind(dns.promises);

const overrides = new Map([
  ["vercel.com", "76.76.21.21"],
  ["api.vercel.com", "76.76.21.21"],
]);

function normalizeOptions(options) {
  if (typeof options === "function") {
    return [{}, options];
  }
  return [options || {}, null];
}

dns.lookup = function lookup(hostname, options, callback) {
  const [normalizedOptions, inferredCallback] = normalizeOptions(options);
  const cb = callback || inferredCallback;
  const address = overrides.get(hostname);
  if (!address || !cb) {
    return originalLookup(hostname, options, callback);
  }
  if (normalizedOptions.all) {
    return process.nextTick(() => cb(null, [{ address, family: 4 }]));
  }
  return process.nextTick(() => cb(null, address, 4));
};

dns.promises.lookup = async function lookup(hostname, options) {
  const address = overrides.get(hostname);
  if (!address) {
    return originalPromisesLookup(hostname, options);
  }
  if (options && options.all) {
    return [{ address, family: 4 }];
  }
  return { address, family: 4 };
};
