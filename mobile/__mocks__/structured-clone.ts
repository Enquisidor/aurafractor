const structuredClone = (val: unknown) => JSON.parse(JSON.stringify(val));
export default structuredClone;
