declare module "@xenova/transformers" {
  export const env: any;
  export function pipeline(...args: any[]): Promise<any>;
}
