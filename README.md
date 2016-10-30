# Item Catalog

application that provides a list of items within a variety of categories as well as provide a user registration and authentication system. Registered users will have the ability to post, edit and delete their own items.

## Prerequisites
1. [**VirtualBox**](https://www.virtualbox.org/)
2. [**Vagrant**](https://www.vagrantup.com/)
3. [**Python**](http://www.python.org/)
4. [**Facebook Account**](https://developers.facebook.com/)
5. [**Google Account**](https://developers.google.com/)

## Installation
1. clone the fullstack-nanodegree-vm
	* git clone ```https://github.com/udacity/fullstack-nanodegree-vm.git ```

2. clone repository or download as zip file
    * git clone ``` https://github.com/elmasria/item-catalog.git ```

## Run Application

1. Start machine ``` $ vagrant up ```

2. Connect to the virtual machine.

	```
	$ vagrant ssh
	$ cd /vagrant/item-catalog
	```

3. Create the database. ``` $ python setup.py ```

4. Initialize Database. ``` $ python initDB.py ```

5. Run Application. ``` $ python app.py ```

6. Navigate to ```http://localhost:5000```

## More Details
1. Routing and Templating made with Flask
2. Uses SQLAlchemy to communicate with the back-end db
3. RESTful API endpoints that return json files
4. Uses Google and Facebook Login to authenticate users
5. Front-end forms and webpages built with boostrap