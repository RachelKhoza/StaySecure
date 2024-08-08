import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import { getUserInfo, getUserLanguages 
} from './githubClient';
import {
  addUser,
  addLanguage,
  getUsers,
  getUsersByLocation
} from './repository';


// Parse the cmd line arguments using yargs
const argv = yargs(hideBin(process.argv)) 
//define fetch cmd to fetch github user info
  .command('fetch [username]', 'Fetch GitHub user info', (yargs) => { 
    return yargs.positional('username', {
      describe: 'GitHub username',
      type: 'string',
      demandOption: true //make username required
    });
  }, async (argv) => {
    if (argv.username) {
      //fetch the info form github
      const userInfo = await getUserInfo(argv.username);
      await addUser(argv.username, userInfo.name, userInfo.location);
      const userLanguages = await getUserLanguages(argv.username);
      const users = await getUsers();
      const user = users.find((user) => user.username === argv.username);
      if (user) {
        for (const language of userLanguages) {
          await addLanguage(user.id, language);
        }
      }
    }
  })
  //define the list cmd to list our users
  .command('list', 'List all users', async () => {
    const users = await getUsers();
    console.log(users);
  })
  //this cmd will list users by location  
  .command('listByLocation [location]', 'List users by location', (yargs) => {
    return yargs.positional('location', {
      describe: 'Location',
      type: 'string',
      demandOption: true
    });
  }, async (argv) => {
    if (argv.location) {
      const users = await getUsersByLocation(argv.location);
      console.log(users);
    }
  })
  .help()
  .argv;