#include<iostream>
#include<algorithm>
#include<fstream>
#include<chrono>
#include <sophus/se3.hpp>

#include<opencv2/core/core.hpp>

#include<System.h>
#include<list>
#include "NDArrayConverter.h"

using namespace std;

#define OK_STATE 2
#define DEPTH
namespace py = pybind11;

namespace pybind11
{
    namespace detail
    {

        template <>
        struct type_caster<cv::KeyPoint>
        {
        public:
            PYBIND11_TYPE_CASTER(cv::KeyPoint, _("cv2.KeyPoint"));

            bool load(handle src, bool)
            {
                py::tuple pt = reinterpret_borrow<py::tuple>(src.attr("pt"));
                auto x = pt[0].cast<float>();
                auto y = pt[1].cast<float>();
                auto size = src.attr("size").cast<float>();
                auto angle = src.attr("angle").cast<float>();
                auto response = src.attr("response").cast<float>();
                auto octave = src.attr("octave").cast<int>();
                auto class_id = src.attr("class_id").cast<int>();
                // (float x, float y, float _size, float _angle, float _response, int _octave, int _class_id)
                value = cv::KeyPoint(x, y, size, angle, response, octave, class_id);

                return true;
            }

            static handle cast(const cv::KeyPoint &kp, return_value_policy, handle defval)
            {
                auto classKP = py::module::import("cv2").attr("KeyPoint");
                auto cvKP = classKP(kp.pt.x, kp.pt.y, kp.size, kp.angle, kp.response, kp.octave, kp.class_id);
                return cvKP.release();
            }
        };

    }
}

class Pyimaislam
{
    private:
        ORB_SLAM3::System *SLAM;
        Sophus::SE3f lastframepose;
        double lasttframe,deltatframe;
        int itime,max_itime;
        Eigen::Vector3f deltat;
        double forwardVelocityDelta;
        std::list<Eigen::Vector3f> list_t;
        std::list<double> frontVelocitys;
        std::list<double> list_tframe;

        double deltf;
        double deltx;
        double delty;
        double deltz;
        //e double position;
        

    public:
        Pyimaislam();
        ~Pyimaislam();
        
        bool reset();
        bool resetVelocity();
#ifdef DEPTH
        double track(cv::Mat im, cv::Mat imDepth, double tframe, bool frontVelocity);
#else
        double track(cv::Mat im, double tframe, bool frontVelocity);
#endif
        double get_deltf();
        double get_deltx();
        double get_delty();
        double get_deltz();
        //e double get_pos();    
        //e double get_tf();
        //e double get_lastf();    
};

Pyimaislam::Pyimaislam()
{
    //Vocabulary/ORBvoc.txt ./Examples/Monocular/TUM1.yaml
    char *a1="/home/aaeon/workspace/orb_slam_endoscope/ORB_SLAM3/Vocabulary/ORBvoc.txt";
#ifdef DEPTH
    char *a2="/home/aaeon/workspace/orb_slam_endoscope/ORB_SLAM3/Examples/RGB-D/Endoscopy.yaml";
    SLAM = new ORB_SLAM3::System(a1,a2,ORB_SLAM3::System::RGBD,true);
#else
    char *a2="/home/aaeon/workspace/orb_slam_endoscope/ORB_SLAM3/Examples/Monocular/Endoscopy.yaml";
    SLAM = new ORB_SLAM3::System(a1,a2,ORB_SLAM3::System::MONOCULAR,true);
#endif    
    max_itime=10;
    resetVelocity();
}

Pyimaislam::~Pyimaislam()
{
    SLAM->Shutdown();
    delete SLAM;
}

bool Pyimaislam::reset()
{
    SLAM->Reset();
    resetVelocity();
}

bool  Pyimaislam::resetVelocity()
{
    itime=0;
    lasttframe = 0;
    deltatframe=0;
    lastframepose = Sophus::SE3f();
    deltat = Eigen::Vector3f();
    forwardVelocityDelta = 0;
    frontVelocitys.clear();
    list_t.clear();
    list_tframe.clear();
    return true;
}

#ifdef DEPTH
double Pyimaislam::track(cv::Mat image, cv::Mat imageDepth, double tframe, bool frontVelocity = true)
#else
double Pyimaislam::track(cv::Mat image, double tframe, bool frontVelocity = true)
#endif
{
    //std::cout << image << std::endl;
#ifdef DEPTH
    auto currentpose = SLAM->TrackRGBD(image, imageDepth, tframe);
#else
    auto currentpose = SLAM->TrackMonocular(image,tframe);
#endif

    if (SLAM->GetTrackingState() != OK_STATE)
    {
        resetVelocity();
        return 0;
    }
    
    // std::cout << "lastpose=" << std::endl<<lastframepose.log() << std::endl;
    // std::cout << "currentpose="<< std::endl<<currentpose.log() << std::endl;
    auto lastpose = lastframepose.inverse();
    //e Eigen::Vector3f pos = currentpose.translation()(0);
    Eigen::Vector3f t = (currentpose * lastpose).translation();

    // compute velocity towards the front
    if(frontVelocity)
    {
        Eigen::Vector3f forward = lastframepose.rotationMatrix() * Eigen::Vector3f::UnitZ();
        double forward_velocity = forward.dot(t);
        frontVelocitys.push_back(forward_velocity);
        forwardVelocityDelta += forward_velocity;
        if(frontVelocitys.size()>max_itime)
        {
            forwardVelocityDelta -= frontVelocitys.front();
            frontVelocitys.pop_front();
        }
    }
    
    list_t.push_back(t);
    list_tframe.push_back(tframe-lasttframe);
    if(list_t.size() > max_itime)
    {
        deltat-=list_t.front();
        list_t.pop_front();
        deltatframe-=list_tframe.front();
        list_tframe.pop_front();
    }
    deltat+=t;
    deltatframe+=(tframe-lasttframe);
    this->deltf = deltatframe;
    this->deltx = deltat(0);
    this->delty = deltat(1);
    this->deltz = deltat(2);
    //e this->position = pos;

    double delta_XYZ = pow(deltat(0), 2) + pow(deltat(1), 2) + pow(deltat(2), 2);
    double velocity = 0;

    if(frontVelocity)
    {
        velocity = forwardVelocityDelta / (deltatframe);
    }
    else
    {
        velocity = sqrt(delta_XYZ) / (deltatframe);
    }

    lastframepose = currentpose;
    if(lasttframe==0)
    {
    	lasttframe = tframe;
    	return 0;
    }
    lasttframe = tframe;
    return velocity;
}

double Pyimaislam::get_deltf()
{
    return deltf;
}

double Pyimaislam::get_deltx()
{
    return deltx;
}

double Pyimaislam::get_delty()
{
    return delty;
}

double Pyimaislam::get_deltz()
{
    return deltz;
}
//e double Pyimaislam::get_pos()
// {
//     return position;
// }
// double Pyimaislam::get_tf()
// {
//     return tframe;
// }
// double Pyimaislam::get_lastf()
// {
//     return lasttframe;
// }

PYBIND11_MODULE(imaislam, m)
{
    NDArrayConverter::init_numpy();

    m.doc() = "IMAI_SLAM3";

    py::class_<Pyimaislam>(m, "Imaislam")
        .def(py::init<>())
        .def("track", &Pyimaislam::track)
        .def("reset", &Pyimaislam::reset)
        .def("reset", &Pyimaislam::resetVelocity)
        .def("getdeltf", &Pyimaislam::get_deltf)
        .def("getdeltx", &Pyimaislam::get_deltx)
        .def("getdelty", &Pyimaislam::get_delty)
        .def("getdeltz", &Pyimaislam::get_deltz)
        //e .def("getpos", &Pyimaislam::get_pos)
        // .def("gettf", &Pyimaislam::get_tf)
        // .def("getlastf", &Pyimaislam::get_lastf)
        ;
}
