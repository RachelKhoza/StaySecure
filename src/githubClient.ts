import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config(); // Load Environment vars

const githubToken = process.env.GITHUB_TOKEN; //


//added this to handle my token error as it was initially not working
export const getUserInfo = async (username: string) => {
  if (!githubToken) {
    throw new Error('GITHUB_TOKEN is not defined');
  }

  //fetch username form github
  const response = await axios.get(`https://api.github.com/users/${username}`, {
    headers: { Authorization: `token ${githubToken}` }
  });
  return response.data; //returning the userdata
};
//
export const getUserLanguages = async (username: string) => {
  if (!githubToken) {
    throw new Error('GITHUB_TOKEN is not defined');
  }

  const response = await 
  axios.get(`https://api.github.com/users/${username}/repos`, {
    headers: { Authorization: `token ${githubToken}` } 
  });
  const languages = new Set<string>(); //create a set to to store the languages
    
  // Iterrate through each repository and add the language to the Set
  response.data.forEach((repo: any) => { 
    if (repo.language) languages.add(repo.language);
  });
  return Array.from(languages);
};